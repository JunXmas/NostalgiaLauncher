"""Thống kê cộng từ dữ liệu thật, không đếm lặp thư mục chung hay bịa lịch sử."""

from dataclasses import replace
from pathlib import Path

from nostalgia.api import Instance, Launcher
from nostalgia.instance.stats import stats_path


def test_empty_and_corrupt_statistics_do_not_invent_playtime(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    assert launcher.load_profile_stats().total_seconds == 0
    instance = launcher.create_instance(Instance("new", "1.21.11"))
    stats_path(launcher.paths, instance.instance_id).write_text("{broken")
    summary = launcher.load_profile_stats()
    assert summary.total_seconds == summary.launch_count == summary.world_count == 0
    assert summary.instance_count == 1 and not summary.favorite_version


def test_custom_game_directory_is_counted_once_and_sessions_are_aggregated(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    first = launcher.create_instance(Instance("first", "1.21.11"))
    second = launcher.create_instance(Instance("second", "1.20.1"))
    shared = tmp_path / "shared-game"
    for name in ("world-one", "world-two"):
        folder = shared / "saves" / name
        folder.mkdir(parents=True)
        (folder / "level.dat").write_bytes(b"world fixture")
    launcher.save_instance(replace(first, game_dir_override=str(shared)))
    launcher.save_instance(replace(second, game_dir_override=str(shared)))
    launcher.record_play_session(first.instance_id, 0, 3600)
    launcher.record_play_session(first.instance_id, 4000, 4300)
    launcher.record_play_session(second.instance_id, 5000, 5600)
    summary = launcher.load_profile_stats()
    assert summary.total_seconds == 4500 and summary.launch_count == 3
    assert summary.world_count == summary.instance_count == 2
    assert summary.favorite_version == "1.21.11"
    assert summary.playtime_text == "1 giờ 15 phút"
