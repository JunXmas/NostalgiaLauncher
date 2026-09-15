"""Nhập thế giới từ thư mục game bên ngoài vào bản chơi Nostalgia.

Chỉ copy thư mục saves/ chứa `level.dat` — thế giới hợp lệ; bỏ qua thư mục không có
`level.dat` (thường là bản sao lỗi hoặc file rác).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress
from nostalgia.storage.files import ensure_dir


def copy_worlds(
    source_game_dir: Path,
    target_game_dir: Path,
    *,
    on_progress: ProgressFn = ignore_progress,
) -> int:
    """Copy thư mục saves từ game_dir nguồn sang game_dir đích.

    Chỉ copy thư mục con chứa level.dat (= thế giới hợp lệ).
    Trả về số thế giới đã copy.
    """
    source_saves = source_game_dir / "saves"
    target_saves = target_game_dir / "saves"

    if not source_saves.is_dir():
        return 0

    ensure_dir(target_saves)

    worlds_to_copy = [
        world_dir.name
        for world_dir in source_saves.iterdir()
        if world_dir.is_dir() and (world_dir / "level.dat").is_file()
    ]

    total = len(worlds_to_copy)
    if total == 0:
        return 0

    on_progress(Progress(stage="Bắt đầu copy thế giới", done=0, total=total))

    for i, world_name in enumerate(worlds_to_copy):
        on_progress(Progress(stage=f"Đang copy {world_name}", done=i, total=total))
        source_world = source_saves / world_name
        target_world = target_saves / world_name
        shutil.copytree(source_world, target_world, dirs_exist_ok=True)

    on_progress(Progress(stage="Hoàn tất copy thế giới", done=total, total=total))
    return total


def list_worlds(game_dir: Path) -> list[str]:
    """Liệt kê tên thư mục thế giới hợp lệ trong saves/."""
    saves_dir = game_dir / "saves"
    if not saves_dir.is_dir():
        return []

    return sorted(
        world_dir.name
        for world_dir in saves_dir.iterdir()
        if world_dir.is_dir() and (world_dir / "level.dat").is_file()
    )
