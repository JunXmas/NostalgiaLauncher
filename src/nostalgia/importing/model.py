"""Hình dạng chung của một bản chơi tìm thấy ở launcher khác.

Nằm riêng chứ không nằm trong `launchers.py` để mỗi scanner là một module độc lập, không
module nào phải import ngược lại module gom.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from nostalgia.modloader.model import LoaderKind


@dataclasses.dataclass(frozen=True, slots=True)
class Found:
    """Đại diện cho một bản chơi Minecraft từ một launcher khác."""

    launcher: str
    instance_name: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind
