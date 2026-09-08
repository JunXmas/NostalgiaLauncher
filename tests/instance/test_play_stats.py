"""Thống kê chơi: cộng dồn đúng, file hỏng không chặn, đếm thế giới chỉ tính thư mục có level.dat."""

from __future__ import annotations

from pathlib import Path

from nostalgia.instance.stats import (
    PlayStats,
    count_worlds,
    format_playtime,
    load_play_stats,
    record_play_session,
    stats_path,
)
from nostalgia.storage.paths import DataPaths


def make_paths(tmp_path: Path) -> DataPaths:
    return DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")


def test_sessions_accumulate_and_survive_a_clock_that_runs_backwards(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    assert load_play_stats(paths, "sinh-ton") == PlayStats()

    first = record_play_session(paths, "sinh-ton", started_at=1_000.0, ended_at=1_000.0 + 125.9)
    assert first == PlayStats(total_seconds=125, launch_count=1, last_played_at=1_125)
    second = record_play_session(paths, "sinh-ton", started_at=5_000.0, ended_at=4_000.0)
    assert second == PlayStats(total_seconds=125, launch_count=2, last_played_at=4_000)
    assert load_play_stats(paths, "sinh-ton") == second


def test_a_corrupt_stats_file_counts_as_never_played(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    record_play_session(paths, "van", 0.0, 60.0)
    stats_path(paths, "van").write_text("{ hỏng")
    assert load_play_stats(paths, "van") == PlayStats()
    stats_path(paths, "van").write_text('{"total_seconds": -5, "launch_count": "hai"}')
    assert load_play_stats(paths, "van") == PlayStats()


def test_worlds_are_save_folders_with_a_level_file(tmp_path: Path) -> None:
    game_dir = tmp_path / "game"
    assert count_worlds(game_dir) == 0
    for name in ("Thế giới 1", "Creative"):
        (game_dir / "saves" / name).mkdir(parents=True)
        (game_dir / "saves" / name / "level.dat").write_bytes(b"\x00")
    (game_dir / "saves" / "rác").mkdir()
    (game_dir / "saves" / "file-lac.txt").write_text("x")
    assert count_worlds(game_dir) == 2


def test_playtime_reads_naturally() -> None:
    assert format_playtime(0) == "chưa chơi"
    assert format_playtime(45) == "dưới 1 phút"
    assert format_playtime(12 * 60 + 30) == "12 phút"
    assert format_playtime(3 * 3600 + 5 * 60) == "3 giờ 05 phút"
    assert format_playtime(2 * 3600) == "2 giờ"
    assert format_playtime(40 * 3600 + 59 * 60) == "40 giờ"
