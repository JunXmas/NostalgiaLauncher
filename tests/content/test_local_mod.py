"""Mod cục bộ: không đổi nguồn, không ghi nhầm, thay có backup và lỗi hoàn tác cả lô."""

from pathlib import Path
from typing import IO, Any
from zipfile import ZipFile

import pytest

from nostalgia.content import local_mod
from nostalgia.content.installed import LEDGER_FILE_NAME, LedgerEntry, load_ledger, save_ledger
from nostalgia.errors import ContentError


def jar(directory: Path, name: str, payload: str = "new") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    with ZipFile(path, "w") as archive:
        archive.writestr("fabric.mod.json", payload)
    return path


def test_copy_batch_preserves_sources_and_only_touches_selected_game(tmp_path: Path) -> None:
    sources = (jar(tmp_path / "input", "A.JAR"), jar(tmp_path / "input", "b.jar"))
    originals = tuple(path.read_bytes() for path in sources)
    game_dir = tmp_path / "selected"
    other = tmp_path / "other"
    other.mkdir()
    result = local_mod.install_local_mods(game_dir, sources)
    assert result.installed == ("A.jar", "b.jar") and result.backup_dir is None
    assert tuple(path.read_bytes() for path in sources) == originals
    assert not tuple(other.iterdir())
    assert tuple((game_dir / "mods" / name).read_bytes() for name in result.installed) == originals


def test_invalid_archive_rejects_whole_batch_before_copy(tmp_path: Path) -> None:
    good = jar(tmp_path / "input", "a.jar")
    bad = tmp_path / "input" / "bad.jar"
    bad.write_text("not a jar")
    with pytest.raises(ContentError, match="JAR hợp lệ"):
        local_mod.install_local_mods(tmp_path / "game", (good, bad))
    assert not (tmp_path / "game" / "mods").exists()


def test_existing_file_skipped_or_backed_up_and_disabled_state_retained(tmp_path: Path) -> None:
    game_dir = tmp_path / "game"
    active = jar(game_dir / "mods", "a.jar", "old-active")
    disabled = jar(game_dir / "mods", "b.jar.disabled", "old-disabled")
    originals = (active.read_bytes(), disabled.read_bytes())
    sources = (jar(tmp_path / "input", "a.jar"), jar(tmp_path / "input", "b.jar"))
    skipped = local_mod.install_local_mods(game_dir, sources)
    assert skipped.installed == () and skipped.skipped == ("a.jar", "b.jar")
    assert (active.read_bytes(), disabled.read_bytes()) == originals
    replaced = local_mod.install_local_mods(game_dir, sources, replace_existing=True)
    assert replaced.installed == ("a.jar", "b.jar.disabled") and replaced.backup_dir
    assert (
        tuple((replaced.backup_dir / name).read_bytes() for name in replaced.installed) == originals
    )
    assert (
        disabled.read_bytes() == sources[1].read_bytes()
        and not (disabled.parent / "b.jar").exists()
    )
    same = local_mod.install_local_mods(game_dir, sources, replace_existing=True)
    assert not same.installed and same.backup_dir is None


def test_duplicate_names_reject_different_contents_but_deduplicate_identical(
    tmp_path: Path,
) -> None:
    first = jar(tmp_path / "one", "a.jar", "one")
    second = jar(tmp_path / "two", "a.jar", "two")
    with pytest.raises(ContentError, match="trùng tên"):
        local_mod.install_local_mods(tmp_path / "game", (first, second))
    second.write_bytes(first.read_bytes())
    result = local_mod.install_local_mods(tmp_path / "game", (first, second))
    assert result.installed == ("a.jar",)


@pytest.mark.parametrize("linked", ["mods", "target", "game"])
def test_symlink_destination_never_changes_external_files(tmp_path: Path, linked: str) -> None:
    outside = tmp_path / "outside"
    old = jar(outside, "a.jar", "external")
    original = old.read_bytes()
    game_dir = tmp_path / "game"
    if linked == "game":
        game_dir.symlink_to(outside, target_is_directory=True)
    else:
        game_dir.mkdir()
        if linked == "mods":
            (game_dir / "mods").symlink_to(outside, target_is_directory=True)
        else:
            (game_dir / "mods").mkdir()
            (game_dir / "mods" / "a.jar").symlink_to(old)
    source = jar(tmp_path / "input", "a.jar")
    with pytest.raises(ContentError, match="liên kết"):
        local_mod.install_local_mods(game_dir, (source,), replace_existing=True)
    assert old.read_bytes() == original


def test_later_write_failure_restores_replacements_and_removes_new_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game_dir = tmp_path / "game"
    old = jar(game_dir / "mods", "a.jar", "old")
    original = old.read_bytes()
    sources = tuple(jar(tmp_path / "input", name) for name in ("a.jar", "b.jar", "c.jar"))
    original_open = Path.open

    def failing_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> IO[Any]:
        if path.name == "c.jar" and mode == "xb":
            raise OSError("simulated disk failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    with pytest.raises(OSError, match="disk failure"):
        local_mod.install_local_mods(game_dir, sources, replace_existing=True)
    assert old.read_bytes() == original
    assert not (old.parent / "b.jar").exists() and not (old.parent / "c.jar").exists()
    assert not tuple(old.parent.glob(".nostalgia-local-*"))


def test_replacement_clears_stale_ledger_and_ledger_failure_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game_dir = tmp_path / "game"
    old = jar(game_dir / "mods", "a.jar", "old")
    original = old.read_bytes()
    save_ledger(old.parent, {"old-project": LedgerEntry("old-project", "Old", "v1", "1", "a.jar")})
    ledger_bytes = (old.parent / LEDGER_FILE_NAME).read_bytes()
    source = jar(tmp_path / "input", "a.jar")

    def fail_save(*_args: object) -> None:
        raise OSError("ledger failure")

    with monkeypatch.context() as patch:
        patch.setattr(local_mod, "save_ledger", fail_save)
        with pytest.raises(OSError, match="ledger failure"):
            local_mod.install_local_mods(game_dir, (source,), replace_existing=True)
    assert old.read_bytes() == original
    assert (old.parent / LEDGER_FILE_NAME).read_bytes() == ledger_bytes
    result = local_mod.install_local_mods(game_dir, (source,), replace_existing=True)
    assert load_ledger(old.parent) == {} and result.backup_dir
    assert (result.backup_dir / LEDGER_FILE_NAME).read_bytes() == ledger_bytes
