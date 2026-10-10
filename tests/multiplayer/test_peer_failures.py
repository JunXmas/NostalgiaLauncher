"""Không hạ cấp âm thầm khi SDP bị sửa; hết đường trực tiếp thì dùng relay."""

from __future__ import annotations

import asyncio
import json
from typing import cast

import pytest
from test_peer_transport import local_ice

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.mux import CLOSE, DATA, pack_mux_frame
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_mux import PeerMux
from nostalgia.multiplayer.peer_stream import PeerStream
from nostalgia.multiplayer.room_watch import RoomWatch
from nostalgia.net.http import HttpClient, HttpResponse


@pytest.mark.parametrize("status", [404, 429, 503])
def test_unavailable_signalling_keeps_relay_without_faking_direct(
    status: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    local_ice(monkeypatch)

    class Http:
        def send(self, *_args: object, **_kwargs: object) -> HttpResponse:
            return HttpResponse(status, b"unavailable")

    class Room(RoomWatch):
        def __init__(self) -> None:
            self.status = RoomStatus(role="joined")
            self.failures: list[str] = []
            self._on_failure = self.failures.append

        def _publish(self, **changes: object) -> None:
            from dataclasses import replace

            self.status = replace(self.status, **changes)  # type: ignore[arg-type]

    async def scenario() -> None:
        room = Room()
        assert await room._connect_game_peer(
            "https://signal.test", "ABCDEFABCDEFGHJKMN", cast(HttpClient, Http())
        )
        assert room.status.connection_kind == "relay" and not room.failures

    asyncio.run(scenario())


def test_corrupted_encrypted_answer_is_rejected_and_rtc_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_ice(monkeypatch)
    from aiortc import RTCPeerConnection

    created: list[RTCPeerConnection] = []

    class TrackedConnection(RTCPeerConnection):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)  # type: ignore[arg-type]
            created.append(self)

    class Http:
        def send(self, *_args: object, **kwargs: object) -> HttpResponse:
            request = json.loads(cast(bytes, kwargs["body"]))
            return HttpResponse(200, json.dumps({"id": request["id"], "body": "a" * 80}).encode())

    monkeypatch.setattr("aiortc.RTCPeerConnection", TrackedConnection)

    async def scenario() -> None:
        with pytest.raises(MultiplayerError, match="xác thực"):
            await connect_peer(
                "https://signal.test", "ABCDEFABCDEFGHJKMN", "game", cast(HttpClient, Http())
            )
        assert created and all(connection.connectionState == "closed" for connection in created)

    asyncio.run(scenario())


def test_remote_eof_preserves_final_minecraft_packet_before_closing() -> None:
    class Incoming:
        async def receive(self) -> bytes:
            return self.frames.pop(0)

        async def close(self) -> None:
            pass

        def __init__(self) -> None:
            self.frames = [
                pack_mux_frame(1, DATA, b"last Minecraft packet"),
                pack_mux_frame(1, CLOSE),
                b"",
            ]

    async def scenario() -> None:
        peer = PeerMux(cast(PeerStream, Incoming()))
        socket = peer.open()
        await peer._runner
        assert await socket.receive() == b"last Minecraft packet"
        assert await socket.receive() == b""
        await peer.close()

    asyncio.run(scenario())
