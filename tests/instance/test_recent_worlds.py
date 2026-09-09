"""Thế giới chơi gần đây: gom trên mọi bản chơi (kể cả bản có thư mục riêng), mới nhất trước,
cắt theo limit, level.dat hỏng vẫn liệt kê, và chỉ MỞ tối đa SCAN_LIMIT file mới nhất."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from nbt_fixture import write_world
from nostalgia.api import Instance, Launcher
from nostalgia.instance.nbt import load_level_summary
from nostalgia.instance.world import SCAN_LIMIT, format_time_ago

NOW = 1_757_500_000.0


def make_launcher(tmp_path: Path) -> Launcher:
    return Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")


def test_worlds_across_instances_come_newest_first_and_respect_the_limit(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    van = launcher.create_instance(Instance(instance_id="van", version_id="1.20.1"))
    rieng = launcher.create_instance(
        Instance(
            instance_id="rieng",
            version_id="1.21.4",
            display_name="Ổ riêng",
            game_dir_override=str(tmp_path / "o-khac" / "rieng"),
        )
    )
    write_world(launcher.instance_game_dir(van), "Nha", "Nhà", int((NOW - 7200) * 1000))
    write_world(launcher.instance_game_dir(van), "Ham", "Hầm mỏ", int((NOW - 30) * 1000))
    write_world(launcher.instance_game_dir(rieng), "Dao", "Đảo", int((NOW - 3 * 86400) * 1000))
    (launcher.instance_game_dir(van) / "saves" / "rac").mkdir()  # không có level.dat → bỏ qua

    worlds = launcher.list_recent_worlds(now=NOW)
    assert [(w.world_name, w.instance_id, w.last_played_text) for w in worlds] == [
        ("Hầm mỏ", "van", "vừa xong"),
        ("Nhà", "van", "2 giờ trước"),
        ("Đảo", "rieng", "3 ngày trước"),
    ]
    assert worlds[2].instance_label == "Ổ riêng" and worlds[2].world_folder == "Dao"
    assert [w.world_folder for w in launcher.list_recent_worlds(limit=2, now=NOW)] == ["Ham", "Nha"]


def test_a_corrupt_level_file_still_lists_by_folder_name_and_mtime(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    instance = launcher.create_instance(Instance(instance_id="van", version_id="1.20.1"))
    level_path = write_world(launcher.instance_game_dir(instance), "Hong", "x", 1)
    level_path.write_bytes(b"khong phai nbt")
    os.utime(level_path, (NOW - 600, NOW - 600))

    [world] = launcher.list_recent_worlds(now=NOW)
    assert (world.world_name, world.world_folder, world.last_played_text) == (
        "Hong",
        "Hong",
        "10 phút trước",
    )


def test_only_the_newest_scan_limit_files_are_opened(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    instance = launcher.create_instance(Instance(instance_id="van", version_id="1.20.1"))
    game_dir = launcher.instance_game_dir(instance)
    for number in range(SCAN_LIMIT + 8):
        level_path = write_world(game_dir, f"w{number:02d}", f"Thế giới {number}", 1)
        os.utime(level_path, (NOW - number * 60, NOW - number * 60))
    opened: list[str] = []

    def counting(level_path: Path) -> object:
        opened.append(level_path.parent.name)
        return load_level_summary(level_path)

    monkeypatch.setattr("nostalgia.instance.world.load_level_summary", counting)
    worlds = launcher.list_recent_worlds(limit=100, now=NOW)
    assert len(opened) == SCAN_LIMIT and "w00" in opened and "w19" not in opened
    assert len(worlds) == SCAN_LIMIT


def test_time_ago_reads_naturally() -> None:
    assert [
        format_time_ago(s) for s in (0, 59, 60, 3599, 3600, 86399, 86400, 29 * 86400, 30 * 86400)
    ] == [
        "vừa xong",
        "vừa xong",
        "1 phút trước",
        "59 phút trước",
        "1 giờ trước",
        "23 giờ trước",
        "1 ngày trước",
        "29 ngày trước",
        "1 tháng trước",
    ]
