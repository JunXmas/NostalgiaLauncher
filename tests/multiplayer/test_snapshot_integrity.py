"""Đổi mod trong phòng chờ không được khởi chạy bộ mod khác với bộ đã mời."""

from pathlib import Path

import pytest

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.snapshot_integrity import verify_snapshot_source
from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot
from nostalgia.operations.cancellation import CancelToken


@pytest.mark.parametrize("change", ["modify", "remove", "add", "symlink"])
def test_host_cannot_launch_a_pack_changed_after_inviting(tmp_path: Path, change: str) -> None:
    source = tmp_path / "game"
    (source / "mods").mkdir(parents=True)
    mod = source / "mods/example.jar"
    mod.write_bytes(b"first")
    cancel_token = CancelToken()
    snapshot = capture_sync_snapshot(
        source,
        tmp_path / "snapshot",
        name="Pack",
        game_version="1.20.1",
        loader_kind="fabric",
        loader_version="0.16.14",
        cancel_token=cancel_token,
    )
    verify_snapshot_source(source, snapshot, frozenset(), cancel_token)
    if change == "modify":
        mod.write_bytes(b"other")
    elif change == "remove":
        mod.unlink()
    elif change == "add":
        (source / "mods/new.jar").write_bytes(b"new")
    else:
        mod.unlink()
        mod.symlink_to(snapshot.folder / "mods/example.jar")
    with pytest.raises(MultiplayerError, match="thay đổi"):
        verify_snapshot_source(source, snapshot, frozenset(), cancel_token)


def test_unshared_mod_and_world_save_do_not_force_pack_recreation(tmp_path: Path) -> None:
    source = tmp_path / "game"
    (source / "mods").mkdir(parents=True)
    (source / "mods/shared.jar").write_bytes(b"shared")
    excluded = source / "mods/private.jar.disabled"
    excluded.write_bytes(b"private")
    cancel_token = CancelToken()
    selection = frozenset({"mods/private.jar.disabled"})
    snapshot = capture_sync_snapshot(
        source,
        tmp_path / "snapshot",
        name="Pack",
        game_version="1.20.1",
        loader_kind="fabric",
        loader_version="0.16.14",
        cancel_token=cancel_token,
        excluded_mods=selection,
    )
    excluded.write_bytes(b"private change")
    (source / "saves").mkdir()
    (source / "saves/world.dat").write_bytes(b"world")
    verify_snapshot_source(source, snapshot, selection, cancel_token)
