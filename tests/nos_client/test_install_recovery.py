"""Lỗi dọn jar hoặc tráo thư mục phải giữ nguyên cả Nos và các mod không liên quan."""

from pathlib import Path

import pytest

from nos_fixture import build_nos_jar
from nostalgia.errors import Cancelled
from nostalgia.nos_client.installation import (
    HISTORY_DIRECTORY,
    inject_mod,
    recover_nos_install,
    remove_mod,
)
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import atomic_write_json


def test_renamed_nos_is_removed_and_unrelated_mod_is_preserved(tmp_path: Path) -> None:
    game_dir = tmp_path / "game"
    mods = game_dir / "mods"
    mods.mkdir(parents=True)
    (mods / "MyNos.jar").write_bytes(build_nos_jar(mod_version="0.4.1"))
    unrelated = mods / "sodium.jar"
    unrelated.write_bytes(b"unchanged")
    addon = mods / "nosclient-addon.jar"
    addon.write_bytes(build_nos_jar(mod_id="another_mod"))
    incoming = tmp_path / "nos-client-0.4.2.jar"
    incoming.write_bytes(build_nos_jar())
    inject_mod(incoming, game_dir)
    assert sorted(path.name for path in mods.iterdir()) == sorted(
        [incoming.name, unrelated.name, addon.name]
    )
    assert unrelated.read_bytes() == b"unchanged"
    assert addon.read_bytes() == build_nos_jar(mod_id="another_mod")
    before = (mods / incoming.name).stat().st_mtime_ns
    receipts = list((game_dir / HISTORY_DIRECTORY).iterdir())
    inject_mod(incoming, game_dir)
    assert (mods / incoming.name).stat().st_mtime_ns == before
    assert list((game_dir / HISTORY_DIRECTORY).iterdir()) == receipts


@pytest.mark.parametrize("operation", ["inject", "remove"])
def test_failure_removing_old_jar_keeps_original_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    game_dir = tmp_path / "game"
    mods = game_dir / "mods"
    mods.mkdir(parents=True)
    previous = mods / "nos-client-0.4.1.jar"
    previous.write_bytes(b"old")
    incoming = tmp_path / "nos-client-0.4.2.jar"
    incoming.write_bytes(b"new")
    unlink = Path.unlink

    def fail_unlink(path: Path, *args: object, **kwargs: object) -> None:
        if path.name == previous.name and path.parent != mods:
            raise PermissionError("Cannot remove previous jar")
        unlink(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.raises(PermissionError):
        inject_mod(incoming, game_dir) if operation == "inject" else remove_mod(game_dir)
    assert previous.read_bytes() == b"old"
    assert list(mods.iterdir()) == [previous]


def test_promote_failure_rolls_back_all_mods(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game_dir = tmp_path / "game"
    mods = game_dir / "mods"
    mods.mkdir(parents=True)
    previous = mods / "nos-client-0.4.1.jar"
    previous.write_bytes(b"old")
    unrelated = mods / "other.jar"
    unrelated.write_bytes(b"keep")
    incoming = tmp_path / "nos-client-0.4.2.jar"
    incoming.write_bytes(b"new")
    replace = Path.replace

    def fail_replace(path: Path, target: str | Path) -> Path:
        if path.name == "mods" and path.parent.name.startswith(".nos-stage-"):
            raise OSError("Simulated promotion failure")
        return replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="promotion failure"):
        inject_mod(incoming, game_dir)
    assert previous.read_bytes() == b"old"
    assert unrelated.read_bytes() == b"keep"
    assert sorted(path.name for path in mods.iterdir()) == [previous.name, unrelated.name]


def test_recovers_a_process_interrupted_between_directory_renames(tmp_path: Path) -> None:
    game_dir = tmp_path / "game"
    receipt = game_dir / HISTORY_DIRECTORY / ("a" * 32)
    before = receipt / "before"
    before.mkdir(parents=True)
    (before / "nos-client-0.4.1.jar").write_bytes(b"known good")
    atomic_write_json(receipt / "receipt.json", {"status": "prepared"})
    recover_nos_install(game_dir)
    assert (game_dir / "mods/nos-client-0.4.1.jar").read_bytes() == b"known good"
    assert not before.exists()


def test_cancelled_install_keeps_previous_jar(tmp_path: Path) -> None:
    game_dir = tmp_path / "game"
    mods = game_dir / "mods"
    mods.mkdir(parents=True)
    previous = mods / "nos-client-0.4.1.jar"
    previous.write_bytes(b"old")
    incoming = tmp_path / "nos-client-0.4.2.jar"
    incoming.write_bytes(b"new")
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        inject_mod(incoming, game_dir, cancel_token=cancel_token)
    assert previous.read_bytes() == b"old"
