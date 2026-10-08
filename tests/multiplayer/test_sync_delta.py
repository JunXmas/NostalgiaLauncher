"""Pack nguồn thật qua HTTPS; guest áp custom và không khôi phục mod host bỏ chọn."""

import hashlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from fabric_fixture import LOADER_VERSION, publish_fabric
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modpack_fixture import MOD_BODY, modpack_project, publish_modpack
from nostalgia.api import Launcher
from nostalgia.content import mrpack
from nostalgia.content.pack_origin import load_pack_origin
from nostalgia.launch.runner import InstallReport
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import atomic_write_json
from nostalgia.version.meta import VersionMeta
from test_api import make_launcher


class SnapshotGateway:
    def __init__(self, folder: Path, manifest: SyncManifest) -> None:
        self.folder, self.manifest = folder, manifest
        self.downloaded: list[str] = []

    def resolve(self, room_code: str) -> SyncManifest:
        del room_code
        return self.manifest

    def download(self, room_code: str, sync_file: SyncFile) -> bytes:
        del room_code
        self.downloaded.append(sync_file.relative_path)
        return (self.folder / sync_file.relative_path).read_bytes()

    def publish(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("guest cannot publish")


@pytest.mark.parametrize("change", ["unchanged", "modified", "removed", "excluded", "disabled"])
def test_original_release_plus_custom_files_and_selected_mods(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    change: str,
) -> None:
    publish_fabric(server_state)
    host = publish_modpack(server, server_state)
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            fabric_meta=server.url("/fabric"),
            modrinth_api=server.url("/modrinth"),
        ),
    )
    monkeypatch.setattr(mrpack, "ALLOWED_HOSTS", (host,))
    instance = launcher.install_modpack(modpack_project(), "host-pack", allowed_hosts=(host,))
    atomic_write_json(
        launcher.paths.version_json(instance.version_id),
        {
            "id": instance.version_id,
            "inheritsFrom": VERSION_ID,
            "mainClass": "Main",
            "libraries": [{"name": "net.fabricmc:fabric-loader:" + LOADER_VERSION}],
        },
    )
    game_dir = launcher.instance_game_dir(instance)
    origin = load_pack_origin(game_dir)
    assert origin and origin.reference.version_id == "v1"
    mod_path = game_dir / "mods/sodium.jar"
    if change == "modified":
        mod_path.write_bytes(b"host privately modified sodium")
    elif change == "removed":
        mod_path.unlink()
    elif change == "disabled":
        mod_path.rename(game_dir / "mods/sodium.jar.disabled")
    (game_dir / "mods/private.jar").write_bytes(b"not on any public repository")
    (game_dir / "config/goi.toml").write_bytes(b"host custom config")
    excluded = frozenset({"mods/sodium.jar"}) if change == "excluded" else frozenset()
    snapshot = launcher.capture_room_modpack(
        "host-pack",
        tmp_path / "snapshot",
        cancel_token=CancelToken(),
        excluded_mods=excluded,
    )
    assert snapshot.manifest.base_pack == origin.reference
    gateway = SnapshotGateway(snapshot.folder, snapshot.manifest)
    report = InstallReport(VersionMeta(instance.version_id, "Main"), tmp_path / "java", 0, 0, 0)
    with patch.object(Launcher, "install_loader", return_value=report) as installer:
        guest = launcher.sync_room_modpack(
            gateway, "fixture", snapshot.manifest, cancel_token=CancelToken()
        )
    guest_dir = launcher.instance_game_dir(guest)
    assert (guest_dir / "mods/private.jar").read_bytes() == b"not on any public repository"
    assert (guest_dir / "config/goi.toml").read_bytes() == b"host custom config"
    assert "mods/private.jar" in gateway.downloaded
    if change in ("removed", "excluded", "disabled"):
        assert not (guest_dir / "mods/sodium.jar").exists()
    if change == "disabled":
        assert (guest_dir / "mods/sodium.jar.disabled").read_bytes() == MOD_BODY
    elif change == "modified":
        assert (guest_dir / "mods/sodium.jar").read_bytes() == b"host privately modified sodium"
        assert "mods/sodium.jar" in gateway.downloaded
    elif change == "unchanged":
        assert (guest_dir / "mods/sodium.jar").read_bytes() == MOD_BODY
        assert "mods/sodium.jar" not in gateway.downloaded
    guest_origin = load_pack_origin(guest_dir)
    assert guest_origin and guest_origin.reference == origin.reference
    baseline = next(
        sync_file
        for sync_file in guest_origin.files
        if sync_file.relative_path == "mods/sodium.jar"
    )
    assert baseline.sha256 == hashlib.sha256(MOD_BODY).hexdigest()
    assert installer.call_args.args == ("fabric", VERSION_ID, LOADER_VERSION)


def test_unverified_older_pack_uses_custom_snapshot_instead_of_guessing_name(
    tmp_path: Path,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path)
    from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot

    source = tmp_path / "game"
    (source / "mods").mkdir(parents=True)
    (source / "mods/private.jar").write_bytes(b"custom")
    snapshot = capture_sync_snapshot(
        source,
        tmp_path / "snapshot",
        name="Better MC",
        game_version="1.20.1",
        loader_kind="vanilla",
        loader_version="",
        cancel_token=CancelToken(),
    )
    assert launcher.describe_sync_snapshot(source, snapshot).manifest.base_pack is None
