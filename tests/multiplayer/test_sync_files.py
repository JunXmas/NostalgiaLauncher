"""Ảnh chụp không chứa thế giới/tài khoản; lỗi tải không để lại bản chơi nửa vời."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from nostalgia.api import Instance, Launcher
from nostalgia.errors import MultiplayerError
from nostalgia.launch.runner import InstallReport
from nostalgia.multiplayer.sync_manifest import manifest_document, parse_sync_manifest
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.version.meta import VersionMeta


class FileGateway:
    def __init__(self, payload: bytes = b"fixture") -> None:
        self.payload = payload
        self.manifest = SyncManifest(
            "Friends",
            "1.20.1",
            "forge",
            "47.4.23",
            (SyncFile("mods/example.jar", hashlib.sha256(b"fixture").hexdigest(), 7),),
        )

    def publish(
        self,
        room_code: str,
        host_ticket: str,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken | None = None,
    ) -> None:
        del room_code, host_ticket, snapshot, cancel_token
        raise AssertionError("guest must never publish")

    def resolve(self, room_code: str) -> SyncManifest | None:
        del room_code
        return self.manifest

    def download(self, room_code: str, sync_file: SyncFile) -> bytes:
        del room_code, sync_file
        return self.payload


def test_snapshot_is_frozen_and_excludes_worlds_accounts_logs(tmp_path: Path) -> None:
    source, destination = tmp_path / "source", tmp_path / "snapshot"
    for relative, payload in [
        ("mods/x.jar", b"mod"),
        ("config/x.toml", b"setting=true"),
        ("saves/world/level.dat", b"world"),
        ("accounts.json", b"secret"),
        ("logs/latest.log", b"secret log"),
    ]:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    snapshot = capture_sync_snapshot(
        source,
        destination,
        name="Pack",
        game_version="1.20.1",
        loader_kind="forge",
        loader_version="47.4.23",
        cancel_token=CancelToken(),
    )
    assert {sync_file.relative_path for sync_file in snapshot.manifest.files} == {
        "mods/x.jar",
        "config/x.toml",
    }
    (source / "mods/x.jar").write_bytes(b"changed")
    assert (snapshot.folder / "mods/x.jar").read_bytes() == b"mod"
    assert not (snapshot.folder / "saves").exists()


def test_snapshot_rejects_symlink(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "mods").mkdir(parents=True)
    (tmp_path / "secret").write_bytes(b"private")
    (source / "mods/private.jar").symlink_to(tmp_path / "secret")
    with pytest.raises(MultiplayerError, match="liên kết"):
        capture_sync_snapshot(
            source,
            tmp_path / "target",
            name="Pack",
            game_version="1.20.1",
            loader_kind="vanilla",
            loader_version="",
            cancel_token=CancelToken(),
        )


def test_guest_installs_exact_loader_into_new_instance_without_overwriting_old(
    tmp_path: Path,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path)
    launcher.create_instance(Instance("existing", "1.20.1", "My own pack"))
    original = tmp_path / "instances/existing/mods/own.jar"
    original.parent.mkdir()
    original.write_bytes(b"keep me")
    gateway = FileGateway()
    report = InstallReport(VersionMeta("1.20.1-forge-47.4.23", "main"), tmp_path / "java", 0, 0, 0)
    with patch.object(Launcher, "install_loader", return_value=report) as installer:
        instance = launcher.sync_room_modpack(
            gateway, "unused-fixture", gateway.manifest, cancel_token=CancelToken()
        )
    assert (
        instance.instance_id != "existing" and instance.version_id == report.version_meta.version_id
    )
    assert original.read_bytes() == b"keep me"
    assert (launcher.instance_game_dir(instance) / "mods/example.jar").read_bytes() == b"fixture"
    assert installer.call_args.args == ("forge", "1.20.1", "47.4.23")


def test_corrupt_file_and_cancel_never_register_partial_instance(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path)
    gateway = FileGateway(b"corrupt")
    with patch.object(Launcher, "install_loader") as installer:
        with pytest.raises(MultiplayerError, match="SHA-256"):
            launcher.sync_room_modpack(
                gateway, "unused-fixture", gateway.manifest, cancel_token=CancelToken()
            )
        assert not installer.called and launcher.list_instances() == ()
    assert list(launcher.paths.instances_dir.iterdir()) == []


@pytest.mark.parametrize(
    "path",
    ["../mods/x", "mods/../x", "mods/x:ads", "mods/CON.jar", "saves/x", "mods//x", "mods/x. "],
)
def test_guest_manifest_rejects_unsafe_paths(path: str) -> None:
    document = manifest_document(FileGateway().manifest)
    document["files"] = [{"path": path, "sha256": "a" * 64, "size": 1}]
    with pytest.raises(MultiplayerError):
        parse_sync_manifest(document)


def test_pack_name_cannot_inject_rich_text_into_instance_cards() -> None:
    document = manifest_document(FileGateway().manifest)
    document["name"] = '<img src="https://attacker.invalid/tracking.png">'
    with pytest.raises(MultiplayerError):
        parse_sync_manifest(document)
