"""Đóng phòng lặp lại khi cả cửa sổ và ứng dụng cùng yêu cầu dọn tài nguyên."""

import pytest

from nostalgia.multiplayer.service import RoomService


@pytest.mark.filterwarnings("error::RuntimeWarning")
def test_repeated_shutdown_releases_room_thread_without_errors() -> None:
    service = RoomService(
        "wss://localhost.invalid/relay",
        on_status=lambda _status: None,
        on_failure=lambda _message: None,
    )
    service.shutdown()
    assert not service._thread.is_alive() and service._loop.is_closed()
    service.shutdown()
    assert not service._thread.is_alive()
