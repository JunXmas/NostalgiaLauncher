"""Phòng chờ không quảng bá LAN trước P2P; mất đường game phải dừng beacon."""

import asyncio
from typing import cast

import pytest
from test_service import wait_for

from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.peer_mux import PeerMux
from nostalgia.multiplayer.service import RoomService
from nostalgia.net.http import HttpClient, HttpResponse


def test_room_without_game_transport_never_advertises_a_joinable_world(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    advertised: list[int] = []

    async def advertise(port: int, _title: str, **_kwargs: object) -> None:
        advertised.append(port)
        await asyncio.Event().wait()

    monkeypatch.setattr(
        "nostalgia.multiplayer.room_network.announce_forever", advertise, raising=False
    )
    monkeypatch.setattr("nostalgia.multiplayer.service.announce_forever", advertise, raising=False)
    statuses: list[RoomStatus] = []

    class Http:
        def send(self, *_args: object, **_kwargs: object) -> HttpResponse:
            return HttpResponse(200, b'{"format":1,"world_ready":false,"direct":true}')

    service = RoomService(
        "wss://signal.test",
        on_status=statuses.append,
        on_failure=lambda _msg: None,
        http_client=cast(HttpClient, Http()),
    )

    class LivePeer:
        closed = False

        async def close(self) -> None:
            self.closed = True

    async def ready() -> None:
        assert service._joiner is not None
        service._joiner.peer = cast(PeerMux, LivePeer())
        service._publish(world_ready=True, connection_kind="direct")

    async def unavailable() -> None:
        service._publish(world_ready=False, connection_kind="failed")

    try:
        service.join("ABCDEFABCDEFGHJKMN").result(3)
        wait_for(lambda: len(statuses) >= 3)
        assert statuses[-1].role == "joined" and not statuses[-1].world_ready
        assert not advertised and service._beacon is None
        service._submit(ready()).result(3)
        wait_for(lambda: bool(advertised))
        assert advertised == [statuses[-1].local_port]
        service._submit(unavailable()).result(3)
        assert service._beacon is None
    finally:
        service.shutdown()


def test_beacon_pauses_until_ready_and_after_transport_loss(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nostalgia.multiplayer.lan import announce_forever, build_beacon

    async def scenario() -> None:
        sent: list[bytes] = []
        ready, turns = False, 0

        class Sender:
            def setsockopt(self, *_args: object) -> None:
                pass

            def sendto(self, payload: bytes, _address: object) -> None:
                sent.append(payload)

            def close(self) -> None:
                pass

        async def tick(_delay: float) -> None:
            nonlocal ready, turns
            turns += 1
            if turns == 3:
                raise asyncio.CancelledError
            ready = turns == 1

        monkeypatch.setattr("nostalgia.multiplayer.lan.socket.socket", lambda *_args: Sender())
        monkeypatch.setattr("nostalgia.multiplayer.lan.local_ipv4_addresses", lambda: {"127.0.0.1"})
        monkeypatch.setattr("nostalgia.multiplayer.lan.asyncio.sleep", tick)
        with pytest.raises(asyncio.CancelledError):
            await announce_forever(54321, "Room", is_ready=lambda: ready)
        assert sent == [build_beacon(54321, "Room")]

    asyncio.run(scenario())
