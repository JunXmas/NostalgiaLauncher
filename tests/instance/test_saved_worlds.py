"""Thế giới của một bản chơi cho cửa sổ chọn: đọc tên / chế độ / hardcore / cheat, icon PNG đã
kiểm (thiếu, hỏng, quá to, khai kích thước khổng lồ → rỗng), level.dat hỏng vẫn liệt kê theo tên
thư mục + mtime, và 100 thế giới đều có mặt, chơi gần nhất trước."""

from __future__ import annotations

import os
import struct
from pathlib import Path

from nbt_fixture import tiny_png, write_world
from nostalgia.instance.world import MAX_ICON_BYTES, format_time_ago, list_worlds, world_icon_url

NOW = 1_757_500_000.0


def at(seconds_ago: float) -> int:
    return int((NOW - seconds_ago) * 1000)


def test_reads_mode_flags_and_the_icon(tmp_path: Path) -> None:
    write_world(tmp_path, "Nha", "Nhà", at(3 * 3600), game_type=0, cheats=True)
    write_world(tmp_path, "Ham", "Hầm mỏ", at(30), game_type=1, hardcore=True)
    (tmp_path / "saves" / "Ham" / "icon.png").write_bytes(tiny_png())
    (tmp_path / "saves" / "rac").mkdir()  # không có level.dat → không phải thế giới

    ham, nha = list_worlds(tmp_path, now=NOW)
    assert (ham.world_folder, ham.world_name, ham.last_played_text) == ("Ham", "Hầm mỏ", "vừa xong")
    assert (ham.game_type, ham.hardcore, ham.cheats) == (1, True, False)
    assert ham.icon_url.startswith("data:image/png;base64,")
    assert (nha.last_played_text, nha.game_type, nha.hardcore, nha.cheats) == (
        "3 giờ trước",
        0,
        False,
        True,
    )
    assert nha.icon_url == "", "không có icon.png → QML dùng ảnh mặc định"


def test_bad_icons_give_no_url(tmp_path: Path) -> None:
    png = tiny_png()
    huge_header = png[:16] + struct.pack(">II", 40_000, 40_000) + png[24:]
    cases = {
        "sai-chu-ky": b"GIF89a\x00\x00" + png[8:],
        "cut": png[:20],
        "qua-to": png + b"\x00" * MAX_ICON_BYTES,
        "khai-khong-lo": huge_header,
        "rong": b"",
    }
    for folder, payload in cases.items():
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "icon.png").write_bytes(payload)
        assert world_icon_url(tmp_path / folder) == "", folder
    assert world_icon_url(tmp_path / "khong-co") == ""


def test_a_corrupt_level_file_still_lists_by_folder_name_and_mtime(tmp_path: Path) -> None:
    level_path = write_world(tmp_path, "Hong", "x", 1, hardcore=True)
    level_path.write_bytes(b"khong phai nbt")
    os.utime(level_path, (NOW - 600, NOW - 600))
    [world] = list_worlds(tmp_path, now=NOW)
    assert (world.world_name, world.world_folder, world.last_played_text) == (
        "Hong",
        "Hong",
        "10 phút trước",
    )
    assert (world.game_type, world.hardcore, world.cheats) == (0, False, False)


def test_a_hundred_worlds_all_come_back_newest_first(tmp_path: Path) -> None:
    for number in range(100):
        write_world(tmp_path, f"w{number:03d}", f"Thế giới {number}", at(number * 60))
    worlds = list_worlds(tmp_path, now=NOW)
    assert len(worlds) == 100
    assert [w.world_folder for w in worlds[:3]] == ["w000", "w001", "w002"]
    assert worlds[-1].world_folder == "w099"
    assert list_worlds(tmp_path / "khong-co", now=NOW) == ()


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
