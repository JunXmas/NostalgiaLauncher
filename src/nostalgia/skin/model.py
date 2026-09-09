"""Dữ liệu skin lộ ra cho giao diện."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PlayerSkin:
    """`skin_path` luôn có (không tải được thì là Steve/Alex mặc định); `cape_path` có thể None.
    `slim` = model Alex (tay 3 pixel), quyết định cách cắt vùng tay khi vẽ."""

    skin_path: Path
    slim: bool
    cape_path: Path | None = None
    is_default: bool = True
