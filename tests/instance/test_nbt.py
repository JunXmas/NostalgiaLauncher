"""Bộ đọc NBT tối giản: lấy đúng tên + mốc chơi cuối, nhảy qua mọi tag khác, và file hỏng
kiểu gì (cụt, không phải gzip, độ dài nói dối, lồng quá sâu, quá to) cũng trả None."""

from __future__ import annotations

import gzip
from pathlib import Path

from nbt_fixture import build_level_dat, deeply_nested_level
from nostalgia.instance.nbt import MAX_DEPTH, MAX_LEVEL_BYTES, LevelSummary, load_level_summary


def test_reads_name_and_last_played_and_skips_every_noise_tag(tmp_path: Path) -> None:
    level_path = tmp_path / "level.dat"
    level_path.write_bytes(build_level_dat("Nhà của Jun", 1_757_400_000_000, nested_depth=5))
    assert load_level_summary(level_path) == LevelSummary("Nhà của Jun", 1_757_400_000_000)


def test_missing_name_gives_an_empty_name_not_none(tmp_path: Path) -> None:
    level_path = tmp_path / "level.dat"
    # Không có LevelName: fixture bỏ nhiễu và ta cắt tag tên bằng cách dựng bằng tay.
    level_path.write_bytes(build_level_dat("", 5_000, noise=False))
    assert load_level_summary(level_path) == LevelSummary("", 5_000)


def test_corrupt_files_return_none_instead_of_raising(tmp_path: Path) -> None:
    healthy = build_level_dat("Ổn", 1_000)
    cases = {
        "cut.dat": healthy[: len(healthy) // 2],
        "not-gzip.dat": b"\x00\x01\x02",
        "empty.dat": b"",
        "lying-length.dat": gzip.compress(b"\x0a\x00\x00\x08\x00\x04Data\xff\xff"),
        "too-deep.dat": deeply_nested_level(MAX_DEPTH + 8),
        "too-big.dat": gzip.compress(b"\x0a\x00\x00" + b"\x00" * (MAX_LEVEL_BYTES + 1)),
    }
    for name, payload in cases.items():
        level_path = tmp_path / name
        level_path.write_bytes(payload)
        assert load_level_summary(level_path) is None, name
    assert load_level_summary(tmp_path / "khong-co.dat") is None


def test_nesting_up_to_the_limit_is_fine(tmp_path: Path) -> None:
    level_path = tmp_path / "level.dat"
    level_path.write_bytes(deeply_nested_level(MAX_DEPTH - 4))
    summary = load_level_summary(level_path)
    assert summary is not None and summary.world_name == "", (
        "LevelName nằm sâu → không lấy, không lỗi"
    )
