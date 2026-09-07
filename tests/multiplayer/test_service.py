"""Dịch vụ phòng chạy ở luồng riêng: host chờ world → nối relay; joiner vào; stop dọn sạch."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterator

import pytest
from fake_relay import FakeRelay
from test_end_to_end import FakeWorld, game_client
from test_gate import MC_HANDSHAKE

from nostalgia.multiplayer.lan import LanWorld
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService


class LoopThread:
    """Relay giả + world giả chạy trong vòng lặp riêng, như máy khác."""

    def __init__(self) -> None:
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.relay, self.world = FakeRelay(), FakeWorld()
        self.run(self.relay.start())
        self.run(self.world.start())

    def run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(5)

    def close(self) -> None:
        self.run(self.world.stop())
        self.run(self.relay.stop())
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(3)


@pytest.fixture
def remote() -> Iterator[LoopThread]:
    loop_thread = LoopThread()
    yield loop_thread
    loop_thread.close()


def wait_for(predicate, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("hết giờ chờ trạng thái")


def make_service(remote: LoopThread, statuses: list[RoomStatus], failures: list[str]):
    return RoomService(
        remote.relay.url,
        on_status=statuses.append,
        on_failure=failures.append,
        detect_world=lambda _timeout: LanWorld(remote.world.port, "Thế giới test"),
    )


def test_host_then_join_then_stop_ends_all_tasks(remote: LoopThread) -> None:
    host_statuses: list[RoomStatus] = []
    join_statuses: list[RoomStatus] = []
    failures: list[str] = []
    host_service = make_service(remote, host_statuses, failures)
    join_service = make_service(remote, join_statuses, failures)
    try:
        host_service.start_hosting().result(5)
        wait_for(lambda: host_statuses and host_statuses[-1].role == "hosting")
        room_code = host_statuses[-1].room_code
        assert len(room_code) == 18 and host_statuses[-1].world_name == "Thế giới test"

        join_service.join(room_code.lower()).result(5)
        assert join_statuses[-1].role == "joined" and join_statuses[-1].local_port > 0
        assert join_statuses[-1].room_code == ""  # joiner không lộ lại mã

        echoed = remote.run(game_client(join_statuses[-1].local_port))
        assert echoed == MC_HANDSHAKE[::-1]
        wait_for(lambda: host_statuses[-1].joiner_count == 1)

        host_service.set_locked(True).result(5)
        assert host_statuses[-1].locked is True

        join_service.stop().result(5)
        assert join_statuses[-1] == RoomStatus()
        host_service.stop().result(5)
        assert host_statuses[-1] == RoomStatus()
        assert failures == []
    finally:
        host_service.shutdown()
        join_service.shutdown()
    assert not host_service._thread.is_alive() and not join_service._thread.is_alive()


def test_join_with_wrong_code_reports_failure_and_stays_idle(remote: LoopThread) -> None:
    statuses: list[RoomStatus] = []
    failures: list[str] = []
    service = make_service(remote, statuses, failures)
    try:
        service.join("ABCDEF").result(5)
        assert failures and "mã phòng" in failures[-1]
        service.join("ABCDEFGHJKMNPQRSTU").result(10)  # đúng dạng, nhưng không ai host
        assert len(failures) == 2 and statuses[-1].role == "idle"
    finally:
        service.shutdown()


def test_unexpected_error_in_the_flow_surfaces_and_stop_still_resets(remote: LoopThread) -> None:
    """Dò LAN nổ lỗi lạ (không phải MultiplayerError): giao diện phải nhận thông báo, và bấm
    dừng vẫn về idle chứ không kẹt vì `await` task đã chết."""
    statuses: list[RoomStatus] = []
    failures: list[str] = []

    def broken_detect(_timeout: float) -> LanWorld | None:
        raise RuntimeError("card mạng nổ")

    service = RoomService(
        remote.relay.url,
        on_status=statuses.append,
        on_failure=failures.append,
        detect_world=broken_detect,
    )
    try:
        service.start_hosting().result(5)
        wait_for(lambda: bool(failures))
        assert failures == ["card mạng nổ"] and statuses[-1].role == "idle"
        service.stop().result(5)
        assert statuses[-1] == RoomStatus()
    finally:
        service.shutdown()
