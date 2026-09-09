"""Thế giới chơi gần đây trên mọi bản chơi — dữ liệu cho ô CHƠI TIẾP ở trang chủ.

Chỉ đọc đĩa. Mỗi bản chơi: liệt kê `saves/*/level.dat`, sắp theo mtime và chỉ MỞ tối đa
`SCAN_LIMIT` file mới nhất (máy có trăm thế giới cũng không làm trang chủ khựng), rồi đọc tên
và mốc chơi cuối bằng bộ đọc NBT tối giản. `level.dat` hỏng vẫn được liệt kê bằng tên thư mục
và mtime — vẫn vào chơi được, game tự dựng lại file.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from nostalgia.instance.model import Instance
from nostalgia.instance.nbt import load_level_summary
from nostalgia.instance.stats import LEVEL_FILE_NAME, SAVES_DIR_NAME
from nostalgia.instance.store import game_dir_of
from nostalgia.storage.paths import DataPaths

DEFAULT_RECENT_LIMIT = 4
SCAN_LIMIT = 12
MINUTE_SECONDS = 60
HOUR_SECONDS = 60 * MINUTE_SECONDS
DAY_SECONDS = 24 * HOUR_SECONDS
MONTH_SECONDS = 30 * DAY_SECONDS


@dataclass(frozen=True, slots=True)
class RecentWorld:
    """Một thế giới có thể vào thẳng: `world_folder` là tên thư mục trong `saves/` — chính là
    giá trị Minecraft nhận ở `--quickPlaySingleplayer`."""

    instance_id: str
    instance_label: str
    world_folder: str
    world_name: str
    last_played_at: int
    last_played_text: str


def format_time_ago(seconds: int) -> str:
    """ "vừa xong" / "N phút trước" / "N giờ trước" / "N ngày trước" / "N tháng trước"."""
    if seconds < MINUTE_SECONDS:
        return "vừa xong"
    if seconds < HOUR_SECONDS:
        return f"{seconds // MINUTE_SECONDS} phút trước"
    if seconds < DAY_SECONDS:
        return f"{seconds // HOUR_SECONDS} giờ trước"
    if seconds < MONTH_SECONDS:
        return f"{seconds // DAY_SECONDS} ngày trước"
    return f"{seconds // MONTH_SECONDS} tháng trước"


def _newest_level_files(game_dir: Path) -> list[tuple[float, Path]]:
    """`(mtime, đường dẫn level.dat)` của tối đa SCAN_LIMIT thế giới mới nhất; thư mục không có
    level.dat bị bỏ qua ngay từ đây."""
    saves_dir = game_dir / SAVES_DIR_NAME
    if not saves_dir.is_dir():
        return []
    found: list[tuple[float, Path]] = []
    with os.scandir(saves_dir) as listing:
        for candidate in listing:
            if not candidate.is_dir():
                continue
            level_path = Path(candidate.path) / LEVEL_FILE_NAME
            try:
                found.append((level_path.stat().st_mtime, level_path))
            except OSError:
                continue
    found.sort(key=lambda pair: pair[0], reverse=True)
    return found[:SCAN_LIMIT]


def list_worlds(game_dir: Path, instance: Instance, *, now: float) -> tuple[RecentWorld, ...]:
    """Thế giới của một bản chơi, mới nhất trước."""
    worlds: list[RecentWorld] = []
    for modified_at, level_path in _newest_level_files(game_dir):
        summary = load_level_summary(level_path)
        if summary is not None and summary.last_played_ms > 0:
            last_played_at = summary.last_played_ms // 1000
        else:
            last_played_at = int(modified_at)
        world_name = summary.world_name if summary is not None else ""
        worlds.append(
            RecentWorld(
                instance_id=instance.instance_id,
                instance_label=instance.label,
                world_folder=level_path.parent.name,
                world_name=world_name or level_path.parent.name,
                last_played_at=last_played_at,
                last_played_text=format_time_ago(max(0, int(now) - last_played_at)),
            )
        )
    worlds.sort(key=lambda world: world.last_played_at, reverse=True)
    return tuple(worlds)


def list_recent_worlds(
    paths: DataPaths,
    instances: Iterable[Instance],
    *,
    limit: int = DEFAULT_RECENT_LIMIT,
    now: float,
) -> tuple[RecentWorld, ...]:
    """Gom thế giới của mọi bản chơi, mới nhất trước, cắt còn `limit`."""
    gathered = [
        world
        for instance in instances
        for world in list_worlds(game_dir_of(paths, instance), instance, now=now)
    ]
    gathered.sort(key=lambda world: world.last_played_at, reverse=True)
    return tuple(gathered[:limit])
