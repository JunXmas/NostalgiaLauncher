"""Proxy báo lỗi đường game ở launcher, không để Minecraft ngắt im lặng."""

import asyncio
from dataclasses import replace
from typing import cast

import pytest
from test_end_to_end import FakeWorld, game_client
from test_peer_transport import Signalling, local_ice

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.peer_mux import PeerMux
from nostalgia.multiplayer.room_watch import RoomWatch
from nostalgia.net.http import HttpClient


@pytest.mark.parametrize("wrong_secret", [False, True])
def test_failed_proxy_connection_reports_stage_without_revealing_secret(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, wrong_secret: bool
) -> None:
    local_ice(monkeypatch)

    async def scenario() -> None:
        errors: list[str] = []
        reported = asyncio.Event()

        def failure(message: str) -> None:
            errors.append(message)
            reported.set()

        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 54321)
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        guest = JoinerBridge("ws://unused", "ABCDEF", "WRONGSECRET1", on_failure=failure)
        writer = None
        try:
            if wrong_secret:
                stream = await connect_peer(
                    "https://signal.test", "ABCDEFABCDEFGHJKMN", "game", cast(HttpClient, Http())
                )
                guest.peer = PeerMux(stream)
            else:
                # Nối loopback không được chờ truy vấn tên máy/card mạng.
                def lookup() -> frozenset[str]:
                    raise AssertionError("Không cần dò interface cho loopback.")

                monkeypatch.setattr("nostalgia.multiplayer.bridge.local_ipv4_addresses", lookup)
            await guest.start()
            reader, writer = await asyncio.open_connection("127.0.0.1", guest.local_port)
            assert await asyncio.wait_for(reader.read(1), 3) == b""
            await asyncio.wait_for(reported.wait(), 3)
            assert len(errors) == 1
            assert "bắt tay" in errors[0] if wrong_secret else "P2P" in errors[0]
            assert all(
                secret not in message
                for secret in ("ABCDEFGHJKMN", "WRONGSECRET1")
                for message in [*errors, *caplog.messages]
            )
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()
            await guest.stop()
            await host.close()

    asyncio.run(scenario())


def test_peer_loss_disables_joining_before_the_next_lobby_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_ice(monkeypatch)

    async def scenario() -> None:
        world = FakeWorld()
        await world.start()
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", world.port)
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal
        lost = asyncio.Event()

        class Http:
            send = signal.send_http

        class Room(RoomWatch):
            def __init__(self) -> None:
                async def idle() -> None:
                    await asyncio.Event().wait()

                self._joiner = JoinerBridge("ws://unused", "ABCDEF", "ABCDEFGHJKMN")
                self._relay_enabled = False
                self._network_task = asyncio.create_task(idle())
                self.status = RoomStatus(role="joined")
                self.failures: list[str] = []
                self._on_failure = self.failure

            def failure(self, message: str) -> None:
                self.failures.append(message)
                lost.set()

            def _publish(self, **changes: object) -> None:
                self.status = replace(self.status, **changes)  # type: ignore[arg-type]

        room = Room()
        try:
            guest = room._joiner
            assert guest is not None
            await guest.start()
            assert await room._connect_game_peer(
                "https://signal.test", "ABCDEFABCDEFGHJKMN", cast(HttpClient, Http())
            )
            before = room.status
            assert before.world_ready and before.connection_kind == "direct"
            assert await asyncio.wait_for(game_client(guest.local_port), 3)
            await host.peer.close()
            await asyncio.wait_for(lost.wait(), 3)
            assert not room.status.world_ready and room.status.connection_kind == "failed"
            assert len(room.failures) == 1
            assert room._network_task is not None
            await asyncio.gather(room._network_task, return_exceptions=True)
            assert room._network_task.cancelled()
        finally:
            guest, room._joiner = room._joiner, None
            if guest is not None:
                await guest.stop()
            if room._network_task is not None:
                room._network_task.cancel()
                await asyncio.gather(room._network_task, return_exceptions=True)
            await host.close()
            await world.stop()

    asyncio.run(scenario())
