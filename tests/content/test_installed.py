"""Sổ theo dõi và thư mục mods/ của một bản chơi: liệt kê, bật/tắt, gỡ — hoàn toàn trên đĩa."""

from __future__ import annotations

from pathlib import Path

import pytest

from nostalgia.content.installed import (
    LEDGER_FILE_NAME,
    LedgerEntry,
    list_installed,
    load_ledger,
    remove_installed,
    save_ledger,
    set_enabled,
)
from nostalgia.errors import ContentError


def seed(game_dir: Path) -> Path:
    mods_dir = game_dir / "mods"
    mods_dir.mkdir(parents=True)
    (mods_dir / "sodium.jar").write_bytes(b"s" * 10)
    (mods_dir / "chep-tay.jar.disabled").write_bytes(b"c" * 20)
    (mods_dir / "ghi-chu.txt").write_text("không phải mod")
    save_ledger(
        mods_dir,
        {
            "AANobbMI": LedgerEntry(
                project_id="AANobbMI",
                title="Sodium",
                version_id="v1",
                version_number="0.5.8",
                file_name="sodium.jar",
            )
        },
    )
    return mods_dir


def test_listing_merges_ledger_and_hand_copied_files(tmp_path: Path) -> None:
    seed(tmp_path)

    installed = list_installed(tmp_path, "mod")

    assert [(m.file_name, m.enabled, m.title) for m in installed] == [
        ("chep-tay.jar", False, ""),
        ("sodium.jar", True, "Sodium"),
    ]
    assert installed[1].label == "Sodium"
    assert installed[0].label == "chep-tay.jar"
    assert installed[0].file_size == 20


def test_toggle_renames_with_the_disabled_suffix_and_is_idempotent(tmp_path: Path) -> None:
    mods_dir = seed(tmp_path)

    set_enabled(tmp_path, "mod", "sodium.jar", False)
    set_enabled(tmp_path, "mod", "sodium.jar", False)
    assert (mods_dir / "sodium.jar.disabled").is_file()
    assert not (mods_dir / "sodium.jar").exists()

    set_enabled(tmp_path, "mod", "sodium.jar", True)
    assert (mods_dir / "sodium.jar").is_file()
    # Sổ vẫn nhận ra mod sau khi bật lại.
    assert list_installed(tmp_path, "mod")[1].title == "Sodium"


def test_remove_deletes_file_and_ledger_line(tmp_path: Path) -> None:
    mods_dir = seed(tmp_path)

    remove_installed(tmp_path, "mod", "sodium.jar")
    remove_installed(tmp_path, "mod", "chep-tay.jar")

    assert list_installed(tmp_path, "mod") == ()
    assert load_ledger(mods_dir) == {}
    with pytest.raises(ContentError):
        remove_installed(tmp_path, "mod", "khong-co.jar")


def test_file_names_cannot_escape_the_folder(tmp_path: Path) -> None:
    seed(tmp_path)
    from nostalgia.errors import UnsafePathError

    with pytest.raises(UnsafePathError):
        set_enabled(tmp_path, "mod", "../sodium.jar", False)


def test_a_corrupt_ledger_does_not_hide_the_files(tmp_path: Path) -> None:
    mods_dir = seed(tmp_path)
    (mods_dir / LEDGER_FILE_NAME).write_text("{ hỏng")

    installed = list_installed(tmp_path, "mod")

    assert [m.file_name for m in installed] == ["chep-tay.jar", "sodium.jar"]
    assert installed[1].title == ""


def test_empty_folder_and_missing_folder_both_list_nothing(tmp_path: Path) -> None:
    assert list_installed(tmp_path, "resourcepack") == ()
    (tmp_path / "shaderpacks").mkdir()
    assert list_installed(tmp_path, "shader") == ()
