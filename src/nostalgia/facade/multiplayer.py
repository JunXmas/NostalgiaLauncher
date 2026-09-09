"""Thao tác CHƠI CHUNG: dựng dịch vụ phòng trỏ tới relay của dự án."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from nostalgia.facade.context import LauncherContext
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService


@dataclass(frozen=True, slots=True)
class MultiplayerOperations(LauncherContext):
    def make_room_service(
        self,
        *,
        on_status: Callable[[RoomStatus], None],
        on_failure: Callable[[str], None],
    ) -> RoomService:
        """Một dịch vụ cho cả đời launcher; gọi `shutdown()` khi đóng cửa sổ."""
        return RoomService(
            self.endpoints.multiplayer_relay, on_status=on_status, on_failure=on_failure
        )
