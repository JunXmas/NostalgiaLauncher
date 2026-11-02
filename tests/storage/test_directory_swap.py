"""Vùng tạm bằng hardlink: nhanh, nhưng bản gốc và bản sao lưu phải còn nguyên byte."""

import json
import os
from pathlib import Path

import pytest

from nostalgia.storage import directory_swap
from nostalgia.storage.directory_swap import (
    commit_directory,
    stage_directory,
    tree_fingerprint,
    tree_hash,
    undo_directory,
)


def _mods(root: Path) -> Path:
    mods = root / "mods"
    mods.mkdir()
    (mods / "a.jar").write_bytes(b"A" * 1000)
    (mods / "b.jar").write_bytes(b"B" * 1000)
    return mods


def test_stage_links_instead_of_copying(tmp_path: Path) -> None:
    mods = _mods(tmp_path)
    stage_directory(mods, tmp_path / "stage")
    assert (tmp_path / "stage/a.jar").stat().st_ino == (mods / "a.jar").stat().st_ino


def test_stage_falls_back_to_copy_when_links_are_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mods = _mods(tmp_path)

    def no_link(*_: object, **__: object) -> None:
        raise OSError("exFAT")

    monkeypatch.setattr(os, "link", no_link)
    stage_directory(mods, tmp_path / "stage")
    assert (tmp_path / "stage/a.jar").read_bytes() == b"A" * 1000
    assert (tmp_path / "stage/a.jar").stat().st_ino != (mods / "a.jar").stat().st_ino


def test_swap_through_linked_stage_then_undo_restores_every_byte(tmp_path: Path) -> None:
    mods = _mods(tmp_path)
    before = tree_hash(mods)
    stage = tmp_path / "stage"
    stage_directory(mods, stage)
    # Đúng kiểu ghi mà installer/sửa mod dùng: file mới + đổi tên + xoá, không ghi tại chỗ.
    (stage / "c.jar").write_bytes(b"C")
    (stage / "a.jar").rename(stage / "a.jar.disabled")
    (stage / "b.jar").unlink()
    receipt = commit_directory(mods, stage, tmp_path / "history", tree_fingerprint(mods))
    assert sorted(p.name for p in mods.iterdir()) == ["a.jar.disabled", "c.jar"]
    undo_directory(mods, tmp_path / "history", receipt)
    assert tree_hash(mods) == before


def test_change_during_preparation_is_detected_without_reading_bytes(tmp_path: Path) -> None:
    mods = _mods(tmp_path)
    original = tree_fingerprint(mods)
    stage = tmp_path / "stage"
    stage_directory(mods, stage)
    (mods / "a.jar").write_bytes(b"other")  # người chơi chép đè một mod trong lúc chuẩn bị
    with pytest.raises(directory_swap.ContentError):
        commit_directory(mods, stage, tmp_path / "history", original)
    assert (mods / "a.jar").read_bytes() == b"other"


def test_undo_refuses_when_mods_changed_after_swap(tmp_path: Path) -> None:
    mods = _mods(tmp_path)
    stage = tmp_path / "stage"
    stage_directory(mods, stage)
    (stage / "c.jar").write_bytes(b"C")
    receipt = commit_directory(mods, stage, tmp_path / "history", tree_fingerprint(mods))
    (mods / "d.jar").write_bytes(b"added later")
    with pytest.raises(directory_swap.ContentError):
        undo_directory(mods, tmp_path / "history", receipt)
    assert (mods / "d.jar").exists()


def test_receipts_written_with_content_hashes_still_undo(tmp_path: Path) -> None:
    """Biên nhận sửa mod tạo trước bản này lưu hash nội dung, không có `format`."""
    mods = _mods(tmp_path)
    history = tmp_path / "history"
    receipt = history / ("0" * 32)
    (receipt / "before").mkdir(parents=True)
    for name in ("a.jar", "b.jar"):
        (receipt / "before" / name).write_bytes((mods / name).read_bytes())
    before = tree_hash(receipt / "before")
    (mods / "a.jar").unlink()
    (receipt / "receipt.json").write_text(
        json.dumps({"status": "applied", "before": before, "after": tree_hash(mods)})
    )
    undo_directory(mods, history, "0" * 32)
    assert tree_hash(mods) == before
