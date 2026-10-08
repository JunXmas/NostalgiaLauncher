"""Chọn mod chỉ ảnh hưởng guest; trạng thái trong game và file riêng không bị thay đổi."""

import json
from pathlib import Path

from nostalgia.api import Instance, Launcher
from nostalgia.content.installed import set_enabled
from nostalgia.multiplayer.sync_chunk import SYNC_CHUNK_BYTES, read_sync_chunk
from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot
from nostalgia.operations.cancellation import CancelToken


def test_preferences_survive_reopen_toggle_and_are_per_instance(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path)
    first = launcher.create_instance(Instance("a", "1.20.1", "Pack A"))
    second = launcher.create_instance(Instance("b", "1.20.1", "Pack B"))
    game_dir = launcher.instance_game_dir(first)
    (game_dir / "mods").mkdir()
    (game_dir / "mods/private.jar").write_bytes(b"private")
    launcher.save_room_share_options("a", frozenset({"mods/private.jar"}))
    reopened = Launcher.for_data_dir(tmp_path)
    assert not reopened.list_room_share_mods("a")[0].shared
    assert reopened.load_room_share_options(second.instance_id) == frozenset()
    assert (game_dir / "mods/private.jar").read_bytes() == b"private"
    set_enabled(game_dir, "mod", "private.jar", False)
    selected = reopened.list_room_share_mods("a")[0]
    assert not selected.enabled and not selected.shared
    (game_dir / "config").mkdir()
    (game_dir / "config/shared.toml").write_bytes(b"shared")
    snapshot = capture_sync_snapshot(
        game_dir,
        tmp_path / "snapshot",
        name="A",
        game_version="1.20.1",
        loader_kind="vanilla",
        loader_version="",
        cancel_token=CancelToken(),
        excluded_mods=reopened.load_room_share_options("a"),
    )
    assert [sync_file.relative_path for sync_file in snapshot.manifest.files] == [
        "config/shared.toml"
    ]
    assert (game_dir / "mods/private.jar.disabled").read_bytes() == b"private"


def test_live_chunk_allowlist_and_commit_fail_if_source_was_removed(tmp_path: Path) -> None:
    source = tmp_path / "game"
    (source / "mods").mkdir(parents=True)
    payload = b"private data" * 30_000
    (source / "mods/private.jar").write_bytes(payload)
    snapshot = capture_sync_snapshot(
        source,
        tmp_path / "snapshot",
        name="A",
        game_version="1.20.1",
        loader_kind="vanilla",
        loader_version="",
        cancel_token=CancelToken(),
    )
    digest = snapshot.manifest.files[0].sha256
    prefix = "a" * 32

    def request(sha256: str, offset: int, length: int) -> bytes:
        return json.dumps(
            {"request_id": prefix, "sha256": sha256, "offset": offset, "length": length}
        ).encode()

    assert (
        read_sync_chunk(snapshot, request(digest, 0, SYNC_CHUNK_BYTES))[32:]
        == payload[:SYNC_CHUNK_BYTES]
    )
    assert (
        read_sync_chunk(
            snapshot, request(digest, SYNC_CHUNK_BYTES, len(payload) - SYNC_CHUNK_BYTES)
        )[32:]
        == payload[SYNC_CHUNK_BYTES:]
    )
    assert read_sync_chunk(snapshot, request(digest, 0, 0)) == prefix.encode()
    assert read_sync_chunk(snapshot, request("b" * 64, 0, 1)) == prefix.encode()
    (snapshot.folder / "mods/private.jar").unlink()
    assert read_sync_chunk(snapshot, request(digest, 0, 0)) != prefix.encode()
