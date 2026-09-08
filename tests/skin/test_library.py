"""Kho skin: thêm không nhân đôi, liệt kê mới nhất trước, gỡ sạch, từ chối file không phải PNG."""

from __future__ import annotations

from pathlib import Path

import pytest

from nostalgia.errors import SkinError
from nostalgia.skin.library import (
    MAX_SKIN_BYTES,
    add_to_library,
    digest_of_file,
    find_entry,
    library_dir,
    list_library,
    remove_from_library,
)

PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def write_png(directory: Path, name: str, body: bytes) -> Path:
    path = directory / name
    path.write_bytes(PNG_HEADER + body)
    return path


def test_same_image_added_twice_stays_one_entry(tmp_path: Path) -> None:
    skins_dir = tmp_path / "skins"
    first = write_png(tmp_path, "a.png", b"jun")
    again = write_png(tmp_path, "b.png", b"jun")
    added = add_to_library(skins_dir, first, name="Jun", slim=False, source="upload", now=100)
    duplicate = add_to_library(skins_dir, again, name="Khác", slim=True, source="import", now=200)

    assert duplicate == added, "cùng ảnh → cùng bản ghi, tên và nguồn của lần đầu được giữ"
    assert [skin_entry.entry_id for skin_entry in list_library(skins_dir)] == [added.entry_id]
    assert added.skin_path.read_bytes() == first.read_bytes()
    assert digest_of_file(first) == added.entry_id
    assert added.source_label == "Đã upload"


def test_library_lists_newest_first_and_skips_broken_pairs(tmp_path: Path) -> None:
    skins_dir = tmp_path / "skins"
    old = add_to_library(
        skins_dir, write_png(tmp_path, "1.png", b"1"), name="Cũ", slim=False, source="ely", now=10
    )
    new = add_to_library(
        skins_dir,
        write_png(tmp_path, "2.png", b"2"),
        name="Mới",
        slim=True,
        source="microsoft",
        now=20,
    )
    (library_dir(skins_dir) / "mo-coi.json").write_text('{"name": "không có png"}')
    (library_dir(skins_dir) / "hong.png").write_bytes(PNG_HEADER)
    (library_dir(skins_dir) / "hong.json").write_text("{ hỏng")

    assert [skin_entry.name for skin_entry in list_library(skins_dir)] == ["Mới", "Cũ"]
    assert find_entry(skins_dir, new.entry_id) == new and find_entry(skins_dir, "khong-co") is None

    remove_from_library(skins_dir, old.entry_id)
    remove_from_library(skins_dir, "khong-co")
    assert [skin_entry.entry_id for skin_entry in list_library(skins_dir)] == [new.entry_id]
    assert not (library_dir(skins_dir) / f"{old.entry_id}.png").exists()


def test_only_small_png_files_are_accepted(tmp_path: Path) -> None:
    skins_dir = tmp_path / "skins"
    not_png = tmp_path / "x.png"
    not_png.write_bytes(b"GIF89a....")
    with pytest.raises(SkinError, match="PNG"):
        add_to_library(skins_dir, not_png, name="x", slim=False, source="import")
    huge = tmp_path / "huge.png"
    huge.write_bytes(PNG_HEADER + b"\x00" * MAX_SKIN_BYTES)
    with pytest.raises(SkinError, match="quá lớn"):
        add_to_library(skins_dir, huge, name="x", slim=False, source="import")
    with pytest.raises(SkinError, match="không đọc được"):
        add_to_library(
            skins_dir, tmp_path / "khong-ton-tai.png", name="x", slim=False, source="import"
        )
    assert list_library(skins_dir) == ()
