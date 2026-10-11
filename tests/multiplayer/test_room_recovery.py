"""Mất P2P thử lại trong cùng phòng; lỗi dịch vụ có giới hạn và rời phòng không hồi sinh."""

import asyncio
import json
import threading
from collections.abc import Iterator
from typing import cast

import pytest
from test_service import wait_for

from nostalgia.multiplayer.peer_mux import PeerMux
from nostalgia.multiplayer.peer_stream import PeerStream
from nostalgia.multiplayer.service import RoomService
from nostalgia.net.http import HttpClient, HttpResponse


class RoomHttp:
    def __init__(self) -> None:
        self.status = 200
        self.document = {"format": 1, "world_ready": True, "direct": True}
        self.calls = 0

    def send(self, *_args: object, **_kwargs: object) -> HttpResponse:
        self.calls += 1
        return HttpResponse(self.status, json.dumps(self.document).encode())


class WaitingStream:
    def __init__(self) -> None:
        self.closed = asyncio.Event()

    async def receive(self) -> bytes:
        await self.closed.wait()
        return b""

    async def close(self) -> None:
        self.closed.set()


@pytest.fixture
def recovery_room(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[RoomService, RoomHttp]]:
    http = RoomHttp()

    async def advertise(*_args: object, **_kwargs: object) -> None:
        await asyncio.Event().wait()

    async def unavailable(*_args: object) -> PeerStream:
        raise TimeoutError

    monkeypatch.setattr("nostalgia.multiplayer.service.announce_forever", advertise)
    monkeypatch.setattr("nostalgia.multiplayer.peer_connection.connect_peer", unavailable)
    service = RoomService(
        "wss://signal.test",
        on_status=lambda _status: None,
        on_failure=lambda _message: None,
        http_client=cast(HttpClient, http),
    )
    try:
        yield service, http
    finally:
        service.shutdown()


def test_retry_keeps_local_proxy_and_room_instead_of_rejoining(
    recovery_room: tuple[RoomService, RoomHttp], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, _http = recovery_room
    service.join("ABCDEFABCDEFGHJKMN").result(3)
    wait_for(lambda: service._status.connection_kind == "failed")
    assert service._status.world_available and not service._status.world_ready
    assert service._status.lobby_verified and service._status.connection_retryable
    joiner, port = service._joiner, service._status.local_port
    connections: list[str] = []

    async def connected(_base: str, room_code: str, _purpose: str, _http: HttpClient) -> PeerStream:
        connections.append(room_code)
        return cast(PeerStream, WaitingStream())

    monkeypatch.setattr("nostalgia.multiplayer.peer_connection.connect_peer", connected)
    service.retry_connection().result(3)
    service.retry_connection().result(3)
    wait_for(lambda: service._status.connection_kind == "direct")
    connected_status = service._status
    assert connected_status.world_ready and not connected_status.connection_note
    assert not connected_status.connection_retryable
    assert service._joiner is joiner and service._status.local_port == port
    assert connections == ["ABCDEFABCDEFGHJKMN"]


def test_room_service_errors_stop_after_three_attempts_and_wait_for_manual_retry(
    recovery_room: tuple[RoomService, RoomHttp], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, http = recovery_room
    http.status = 503
    original_sleep = asyncio.sleep

    async def fast_poll(seconds: float) -> None:
        await original_sleep(0 if seconds == 15 else seconds)

    monkeypatch.setattr("nostalgia.multiplayer.room_watch.asyncio.sleep", fast_poll)
    service.join("ABCDEFABCDEFGHJKMN").result(3)
    wait_for(lambda: service._status.connection_kind == "failed")
    assert http.calls == 3
    assert (
        service._status.connection_retryable and "Kiểm tra mạng" in service._status.connection_note
    )
    assert service._network_task is not None and service._network_task.done()
    assert not service._status.world_ready


def test_room_service_outage_does_not_disconnect_a_working_peer(
    recovery_room: tuple[RoomService, RoomHttp], monkeypatch: pytest.MonkeyPatch
) -> None:
    service, http = recovery_room
    original_sleep = asyncio.sleep

    async def fast_poll(seconds: float) -> None:
        await original_sleep(0.01 if seconds in (15, 60) else seconds)

    async def connected(*_args: object) -> PeerStream:
        return cast(PeerStream, WaitingStream())

    monkeypatch.setattr("nostalgia.multiplayer.room_watch.asyncio.sleep", fast_poll)
    monkeypatch.setattr("nostalgia.multiplayer.peer_connection.connect_peer", connected)
    service.join("ABCDEFABCDEFGHJKMN").result(3)
    wait_for(lambda: service._status.connection_kind == "direct")
    assert service._joiner is not None
    peer = service._joiner.peer
    before = http.calls
    http.status = 503
    wait_for(lambda: http.calls >= before + 4)
    assert service._status.connection_kind == "direct" and service._status.world_ready
    assert "P2P hiện tại vẫn hoạt động" in service._status.connection_note
    assert not service._status.connection_retryable
    assert peer is not None and not peer.closed and service._joiner.peer is peer


@pytest.mark.parametrize("status,document", [(404, {}), (200, {"format": 9})])
def test_closed_or_invalid_room_requests_a_new_invitation_instead_of_retrying(
    recovery_room: tuple[RoomService, RoomHttp], status: int, document: dict[str, object]
) -> None:
    service, http = recovery_room
    http.status, http.document = status, document  # type: ignore[assignment]
    service.join("ABCDEFABCDEFGHJKMN").result(3)
    wait_for(lambda: service._status.connection_kind == "failed")
    assert not service._status.connection_retryable and not service._status.world_ready
    service.retry_connection().result(3)
    assert http.calls == 1


def test_leaving_during_retry_cannot_reopen_the_room(
    recovery_room: tuple[RoomService, RoomHttp],
) -> None:
    service, http = recovery_room
    service.join("ABCDEFABCDEFGHJKMN").result(3)
    wait_for(lambda: service._status.connection_kind == "failed")
    entered, released = threading.Event(), threading.Event()

    class ClosingPeer:
        async def close(self) -> None:
            entered.set()
            while not released.is_set():
                await asyncio.sleep(0.01)

    async def install_old_peer() -> None:
        assert service._joiner is not None
        service._joiner.peer = cast(PeerMux, ClosingPeer())

    service._submit(install_old_peer()).result(3)
    retried = service.retry_connection()
    try:
        assert entered.wait(3)
        service.stop().result(3)
    finally:
        released.set()
        retried.result(3)
    assert service._status.role == "idle" and service._joiner is None
    assert http.calls == 1
