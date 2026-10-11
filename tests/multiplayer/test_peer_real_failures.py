"""ICE/DTLS thật: lệch đồng hồ và mất kênh giữa file không được làm hỏng đồng bộ."""

import asyncio
import concurrent.futures
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from test_end_to_end import FakeWorld, game_client
from test_peer_transport import Signalling, local_ice

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_download import PeerDownload
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.peer_mux import PeerMux
from nostalgia.multiplayer.sync_chunk import read_sync_chunk
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.operations.cancellation import CancelToken


class FastSignalling(Signalling):
    def send_http(self, _method: str, _url: str, **kwargs: object) -> HttpResponse:
        document = json.loads(cast(bytes, kwargs["body"]))
        self.purposes.append(document["purpose"])
        document["expires_at"] = int(time.time()) + 45
        future: concurrent.futures.Future[bytes] = concurrent.futures.Future()
        self.requests[document["id"]] = future
        assert self.host.peer is not None
        self.loop.call_soon_threadsafe(self.host.peer.request, json.dumps(document).encode())
        return HttpResponse(200, future.result(3))


@pytest.mark.parametrize("clock_skew", [-120, -3, 120])
@pytest.mark.parametrize("purpose", ["game", "sync"])
def test_two_peers_work_when_host_clock_differs_from_signalling_server(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    clock_skew: int,
    purpose: str,
) -> None:
    local_ice(monkeypatch)
    monkeypatch.setattr(
        "nostalgia.multiplayer.peer_host.time",
        SimpleNamespace(time=lambda: time.time() + clock_skew, monotonic=time.monotonic),
    )
    content = b"private modpack bytes"
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/custom.jar").write_bytes(content)
    sync_file = SyncFile("mods/custom.jar", hashlib.sha256(content).hexdigest(), len(content))

    async def scenario() -> None:
        world = FakeWorld()
        await world.start()
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", world.port)
        host.sync_snapshot = SyncSnapshot(
            SyncManifest("Friends", "1.20.1", "fabric", "0.16.0", (sync_file,)), tmp_path
        )
        host.peer = PeerHost(host)
        signal = FastSignalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        http_client = cast(HttpClient, Http())
        guest = JoinerBridge("ws://unused", "ABCDEF", "ABCDEFGHJKMN")
        receiver = PeerDownload("https://signal.test", http_client, disable_on_failure=False)
        try:
            if purpose == "sync":
                result = await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken())
                assert result == content
            else:
                stream = await connect_peer(
                    "https://signal.test", "ABCDEFABCDEFGHJKMN", "game", http_client
                )
                guest.peer = PeerMux(stream)
                await guest.start()
                assert await asyncio.wait_for(game_client(guest.local_port), 5)
            assert signal.purposes == [purpose]
        finally:
            await receiver.close()
            await guest.stop()
            await host.close()
            await world.stop()

    asyncio.run(scenario())


def test_custom_file_continues_at_missing_chunk_after_peer_window_closes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    local_ice(monkeypatch)
    content = b"selected resource pack" * 40000
    (tmp_path / "resourcepacks").mkdir()
    (tmp_path / "resourcepacks/custom.zip").write_bytes(content)
    sync_file = SyncFile(
        "resourcepacks/custom.zip", hashlib.sha256(content).hexdigest(), len(content)
    )
    offsets: list[int] = []

    def closing_chunk(snapshot: SyncSnapshot, payload: bytes) -> bytes:
        offset = json.loads(payload)["offset"]
        offsets.append(offset)
        # Giả lập host hết cửa sổ cấp quyền sau khối đầu; lần nối mới tiếp tục đúng khối.
        return b"" if len(offsets) == 2 else read_sync_chunk(snapshot, payload)

    monkeypatch.setattr("nostalgia.multiplayer.peer_host.read_sync_chunk", closing_chunk)

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 0)
        host.sync_snapshot = SyncSnapshot(
            SyncManifest("Friends", "1.20.1", "fabric", "0.16.0", (sync_file,)), tmp_path
        )
        host.peer = PeerHost(host)
        signal = FastSignalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        receiver = PeerDownload(
            "https://signal.test", cast(HttpClient, Http()), disable_on_failure=False
        )
        try:
            assert (
                await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken()) == content
            )
            assert signal.purposes == ["sync", "sync"]
            assert offsets.count(0) == 1, "không tải lại phần đã nhận khi nối lại"
        finally:
            await receiver.close()
            await host.close()

    asyncio.run(scenario())
