"""Dữ liệu chơi chung lộ ra cho giao diện. Không chứa `room_secret` dưới dạng riêng lẻ."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RoomRole = Literal["idle", "waiting_world", "hosting", "joined"]


@dataclass(frozen=True, slots=True)
class RoomStatus:
    """Ảnh chụp trạng thái phòng để giao diện vẽ.

    `room_code` chỉ có ở host (để đọc cho bạn); phía joiner rỗng vì đã nhập rồi, không cần lộ
    lại. `local_port` là cổng proxy cục bộ phía joiner; Minecraft tự thấy nó trong tab LAN.
    """

    role: RoomRole = "idle"
    room_code: str = ""
    local_port: int = 0
    joiner_count: int = 0
    locked: bool = False
    world_name: str = ""
