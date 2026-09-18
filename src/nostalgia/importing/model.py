"""Hình dạng chung của một bản chơi tìm thấy ở launcher khác, và cách tra thư mục của nó.

Ở riêng đây chứ không nằm trong `launchers.py` để từng scanner được tách ra file riêng khi
file kia chạm trần 200 dòng (GLOSSARY §1.5) mà không sinh vòng import ngược lại.
"""

from __future__ import annotations

import dataclasses
import os
import platform
from pathlib import Path

from nostalgia.modloader.model import LoaderKind


@dataclasses.dataclass(frozen=True, slots=True)
class Found:
    """Đại diện cho một instance Minecraft từ một launcher khác."""

    launcher: str
    instance_name: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind


def platform_dir(linux: str, darwin: str, windows: str) -> Path | None:
    """Trả thư mục theo hệ điều hành, hoặc None nếu không hỗ trợ."""
    sys_plat = platform.system()
    if sys_plat == "Linux":
        return Path(linux).expanduser()
    if sys_plat == "Darwin":
        return Path(darwin).expanduser()
    if sys_plat == "Windows":
        return Path(os.environ.get("APPDATA", "~")) / windows
    return None
