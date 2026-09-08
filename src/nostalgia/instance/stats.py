"""Thống kê chơi của một bản chơi: tổng giờ chơi, số lần chạy, lần chơi cuối, số thế giới.

Ghi ở `stats.json` cạnh `instance.json` — xoá thư mục bản chơi là xoá luôn số liệu của nó,
không để lại bản ghi mồ côi (cùng lý do kho instance không dùng một file danh sách chung).
File hỏng thì coi như chưa chơi: một số liệu mất không được phép chặn nút CHƠI.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path

from nostalgia.errors import DataFileError
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping
from nostalgia.storage.files import atomic_write_json, ensure_dir
from nostalgia.storage.files import read_json as read_json_file
from nostalgia.storage.paths import DataPaths

STATS_FILE_NAME = "stats.json"
SAVES_DIR_NAME = "saves"
LEVEL_FILE_NAME = "level.dat"


@dataclass(frozen=True, slots=True)
class PlayStats:
    """Số liệu cộng dồn. `last_played_at` là mốc epoch (giây), 0 = chưa chơi lần nào."""

    total_seconds: int = 0
    launch_count: int = 0
    last_played_at: int = 0


@dataclass(frozen=True, slots=True)
class InstanceStats:
    """Số liệu để hiện trên thẻ bản chơi: `PlayStats` cộng thêm những gì đếm được trên đĩa."""

    play: PlayStats
    world_count: int
    mod_count: int

    @property
    def playtime_text(self) -> str:
        return format_playtime(self.play.total_seconds)


def stats_path(paths: DataPaths, instance_id: str) -> Path:
    return paths.instance_dir(instance_id) / STATS_FILE_NAME


def load_play_stats(paths: DataPaths, instance_id: str) -> PlayStats:
    """Chưa có hay hỏng đều là `PlayStats()` — không phải lỗi."""
    path = stats_path(paths, instance_id)
    if not path.is_file():
        return PlayStats()
    try:
        fields = as_mapping(read_json_file(path))
    except DataFileError:
        return PlayStats()
    return PlayStats(
        total_seconds=max(0, as_integer(fields.get("total_seconds")) or 0),
        launch_count=max(0, as_integer(fields.get("launch_count")) or 0),
        last_played_at=max(0, as_integer(fields.get("last_played_at")) or 0),
    )


def record_play_session(
    paths: DataPaths, instance_id: str, started_at: float, ended_at: float
) -> PlayStats:
    """Cộng một phiên chơi vào số liệu và ghi lại. Đồng hồ lùi (ended < started) tính là 0 giây."""
    previous = load_play_stats(paths, instance_id)
    seconds = max(0, int(ended_at - started_at))
    updated = replace(
        previous,
        total_seconds=previous.total_seconds + seconds,
        launch_count=previous.launch_count + 1,
        last_played_at=max(previous.last_played_at, int(ended_at)),
    )
    ensure_dir(paths.instance_dir(instance_id))
    document: JsonValue = {
        "total_seconds": updated.total_seconds,
        "launch_count": updated.launch_count,
        "last_played_at": updated.last_played_at,
    }
    atomic_write_json(stats_path(paths, instance_id), document)
    return updated


def count_worlds(game_dir: Path) -> int:
    """Số thế giới = số thư mục con của `saves/` có `level.dat`. Thư mục rác không tính."""
    saves_dir = game_dir / SAVES_DIR_NAME
    if not saves_dir.is_dir():
        return 0
    total = 0
    with os.scandir(saves_dir) as entries:
        for found in entries:
            if found.is_dir() and (Path(found.path) / LEVEL_FILE_NAME).is_file():
                total += 1
    return total


def format_playtime(total_seconds: int) -> str:
    """ "chưa chơi", "dưới 1 phút", "12 phút", "3 giờ 05 phút", "40 giờ"."""
    if total_seconds <= 0:
        return "chưa chơi"
    minutes, _ = divmod(total_seconds, 60)
    if minutes == 0:
        return "dưới 1 phút"
    hours, minutes = divmod(minutes, 60)
    if hours == 0:
        return f"{minutes} phút"
    if hours >= 10 or minutes == 0:
        return f"{hours} giờ"
    return f"{hours} giờ {minutes:02d} phút"
