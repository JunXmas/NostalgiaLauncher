"""Hai đầu ICE/DTLS thật trên loopback; game ghép kênh và file không đi qua relay."""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import time
from pathlib import Path
from typing import cast

import pytest
from test_end_to_end import FakeWorld, game_client

pytest.importorskip("aiortc")
from aiortc import RTCConfiguration

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.mux import PEER_RESPONSE, unpack_mux_frame
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_download import PeerDownload
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.peer_mux import PeerMux
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.operations.cancellation import CancelToken


class Signalling:
    host_ticket = "ticket"
    closed = False

    def __init__(self, host: HostRelay) -> None:
        self.host = host
        self.loop = asyncio.get_running_loop()
        self.requests: dict[str, concurrent.futures.Future[bytes]] = {}
        self.purposes: list[str] = []

    async def send(self, payload: bytes) -> None:
        frame = unpack_mux_frame(payload)
        assert frame and frame[1] == PEER_RESPONSE
        document = json.loads(frame[2])
        self.requests[document["id"]].set_result(frame[2])

    async def receive(self) -> bytes:
        return b""

    async def close(self) -> None:
        pass

    def send_http(self, _method: str, _url: str, **kwargs: object) -> HttpResponse:
        document = json.loads(cast(bytes, kwargs["body"]))
        self.purposes.append(document["purpose"])
        document["expires_at"] = int(time.time()) + 45
        future: concurrent.futures.Future[bytes] = concurrent.futures.Future()
        self.requests[document["id"]] = future
        assert self.host.peer is not None
        self.loop.call_soon_threadsafe(self.host.peer.request, json.dumps(document).encode())
        return HttpResponse(200, future.result(15))


def local_ice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aioice.ice.get_host_addresses", lambda **_kw: ["127.0.0.1"])
    monkeypatch.setattr(
        "nostalgia.multiplayer.peer_connection.build_peer_configuration",
        lambda: RTCConfiguration(iceServers=[]),
    )
    monkeypatch.setattr(
        "nostalgia.multiplayer.peer_host.build_peer_configuration",
        lambda: RTCConfiguration(iceServers=[]),
    )


def test_real_dtls_game_reuses_one_peer_for_ping_and_login(monkeypatch: pytest.MonkeyPatch) -> None:
    local_ice(monkeypatch)

    async def scenario() -> None:
        world = FakeWorld()
        await world.start()
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", world.port)
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        bridge = JoinerBridge("ws://unused", "ABCDEF", "ABCDEFGHJKMN")
        try:
            stream = await connect_peer(
                "https://signal.test", "ABCDEFABCDEFGHJKMN", "game", cast(HttpClient, Http())
            )
            bridge.peer = PeerMux(stream)
            await bridge.start()
            first = await asyncio.wait_for(game_client(bridge.local_port), 5)
            second = await asyncio.wait_for(game_client(bridge.local_port), 5)
            assert first == second and first
            host.locked = True
            assert await asyncio.wait_for(game_client(bridge.local_port), 5) == b""
            host.locked = False
            assert await asyncio.wait_for(game_client(bridge.local_port), 5) == first
            assert signal.purposes == ["game"], "one negotiation, no HTTP per Minecraft packet"
            assert stream.connection.connectionState == "connected"
        finally:
            await asyncio.wait_for(bridge.stop(), 5)
            await asyncio.wait_for(host.close(), 5)
            await asyncio.wait_for(world.stop(), 5)
        assert not host.peer.connections and not host.peer.games

    asyncio.run(scenario())


def test_real_dtls_sync_chunks_reuse_channel_and_only_read_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local_ice(monkeypatch)
    content = b"custom resource" * 50000
    (tmp_path / "resourcepacks").mkdir()
    (tmp_path / "resourcepacks/selected.zip").write_bytes(content)
    sync_file = SyncFile(
        "resourcepacks/selected.zip", hashlib.sha256(content).hexdigest(), len(content)
    )

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 0)
        host.sync_snapshot = SyncSnapshot(
            SyncManifest("Friends", "1.20.1", "fabric", "0.16.0", (sync_file,)), tmp_path
        )
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        receiver = PeerDownload("https://signal.test", cast(HttpClient, Http()))
        try:
            received = await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken())
            assert received == content
            assert (
                await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken()) == content
            )
            assert signal.purposes == ["sync"]
        finally:
            await receiver.close()
            await asyncio.wait_for(host.close(), 5)
        assert not host.peer.connections

    asyncio.run(scenario())
