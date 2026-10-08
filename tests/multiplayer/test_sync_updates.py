"""Các phòng khác nhau cập nhật đúng pack, bảo toàn dữ liệu riêng và lựa chọn khách."""

import hashlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from nostalgia.api import Instance, Launcher
from nostalgia.errors import MultiplayerError
from nostalgia.instance.store import unregister_instance
from nostalgia.instance.sync_identity import ensure_sync_pack_id
from nostalgia.instance.sync_receipt import load_sync_receipt
from nostalgia.launch.runner import InstallReport
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest
from nostalgia.operations.cancellation import CancelToken
from nostalgia.version.meta import VersionMeta


class UpdateGateway:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self.downloaded: list[str] = []
        self.replace_payloads(payloads)

    def replace_payloads(self, payloads: dict[str, bytes]) -> None:
        self.payloads = payloads
        self.manifest = SyncManifest(
            "Same name",
            "1.20.1",
            "vanilla",
            "",
            tuple(
                SyncFile(path, hashlib.sha256(payload).hexdigest(), len(payload))
                for path, payload in payloads.items()
            ),
            pack_id="a" * 32,
            owner_id="host_A",
        )

    def resolve(self, _room_code: str) -> SyncManifest:
        return self.manifest

    def download(self, _room_code: str, sync_file: SyncFile) -> bytes:
        self.downloaded.append(sync_file.relative_path)
        return self.payloads[sync_file.relative_path]

    def publish(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("guest cannot publish")


@pytest.fixture
def update_rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Launcher, UpdateGateway]:
    launcher = Launcher.for_data_dir(tmp_path)
    report = InstallReport(VersionMeta("1.20.1", "Main"), tmp_path / "java", 0, 0, 0)
    monkeypatch.setattr(Launcher, "install_loader", lambda *_args, **_kwargs: report)
    return launcher, UpdateGateway(
        {
            "mods/a.jar": b"a",
            "mods/b.jar": b"b",
            "config/a.toml": b"old",
            "resourcepacks/art.zip": b"texture",
        }
    )


def sync(
    launcher: Launcher, gateway: UpdateGateway, excluded: frozenset[str] = frozenset()
) -> Instance:
    return launcher.sync_room_modpack(
        gateway,
        "new room code",
        gateway.manifest,
        cancel_token=CancelToken(),
        excluded_paths=excluded,
    )


def test_update_downloads_delta_preserves_worlds_and_local_mods_and_texture_choices(
    update_rig: tuple[Launcher, UpdateGateway],
) -> None:
    launcher, gateway = update_rig
    created = sync(launcher, gateway, frozenset({"mods/b.jar"}))
    game_dir = launcher.instance_game_dir(created)
    (game_dir / "saves/world").mkdir(parents=True)
    (game_dir / "saves/world/level.dat").write_bytes(b"world")
    (game_dir / "mods/local.jar").write_bytes(b"local")
    gateway.downloaded.clear()
    gateway.replace_payloads(
        {
            "mods/a.jar": b"a",
            "mods/b.jar": b"b",
            "mods/new.jar": b"new",
            "config/a.toml": b"changed",
            "resourcepacks/art.zip": b"new texture",
        }
    )
    review = launcher.review_room_modpack(gateway.manifest)
    assert review.instance_id == created.instance_id
    assert (
        next(choice for choice in review.choices if choice.relative_path == "mods/new.jar").selected
        is False
    )
    updated = sync(launcher, gateway, frozenset({"mods/b.jar", "mods/new.jar"}))
    assert updated.instance_id == created.instance_id and len(launcher.list_instances()) == 1
    assert gateway.downloaded == ["config/a.toml", "resourcepacks/art.zip"]
    assert (game_dir / "saves/world/level.dat").read_bytes() == b"world"
    assert (game_dir / "mods/local.jar").read_bytes() == b"local"
    assert (game_dir / "resourcepacks/art.zip").read_bytes() == b"new texture"
    assert not (game_dir / "mods/b.jar").exists() and not (game_dir / "mods/new.jar").exists()
    backups = tuple((game_dir / ".nostalgia-sync-backups").glob("*/game/config/a.toml"))
    assert len(backups) == 1 and backups[0].read_bytes() == b"old"
    gateway.replace_payloads({"config/a.toml": b"changed"})
    sync(launcher, gateway)
    assert not (game_dir / "mods/a.jar").exists()
    assert (game_dir / "mods/local.jar").exists()
    assert not (game_dir / "resourcepacks/art.zip").exists()


@pytest.mark.parametrize("field", ["pack_id", "owner_id"])
def test_same_name_new_pack_or_different_owner_never_overwrites(
    update_rig: tuple[Launcher, UpdateGateway], field: str
) -> None:
    launcher, gateway = update_rig
    first = sync(launcher, gateway)
    gateway.manifest = (
        replace(gateway.manifest, pack_id="b" * 32)
        if field == "pack_id"
        else replace(gateway.manifest, owner_id="b" * 32)
    )
    assert not launcher.review_room_modpack(gateway.manifest).instance_id
    second = sync(launcher, gateway)
    assert first.instance_id != second.instance_id and len(launcher.list_instances()) == 2


def test_client_collision_refuses_before_download_and_restores_disabled_state(
    update_rig: tuple[Launcher, UpdateGateway],
) -> None:
    launcher, gateway = update_rig
    created = sync(launcher, gateway)
    game_dir = launcher.instance_game_dir(created)
    (game_dir / "mods/a.jar").rename(game_dir / "mods/a.jar.disabled")
    (game_dir / "mods/local.jar").write_bytes(b"my own")
    gateway.replace_payloads({"mods/a.jar": b"new", "mods/local.jar": b"host"})
    gateway.downloaded.clear()
    with pytest.raises(MultiplayerError, match="trùng"):
        sync(launcher, gateway)
    assert not gateway.downloaded
    assert (game_dir / "mods/local.jar").read_bytes() == b"my own"
    gateway.replace_payloads({"mods/a.jar": b"new"})
    sync(launcher, gateway)
    assert not (game_dir / "mods/a.jar.disabled").exists()
    assert (game_dir / "mods/a.jar").read_bytes() == b"new"


def test_failed_commit_rolls_back_files_and_receipt(
    update_rig: tuple[Launcher, UpdateGateway],
) -> None:
    launcher, gateway = update_rig
    created = sync(launcher, gateway)
    previous = load_sync_receipt(launcher.paths, created.instance_id)
    game_dir = launcher.instance_game_dir(created)
    gateway.replace_payloads({"mods/a.jar": b"changed", "mods/new.jar": b"new"})
    with (
        patch("nostalgia.facade.sync_update.save_instance", side_effect=OSError("disk full")),
        pytest.raises(OSError),
    ):
        sync(launcher, gateway)
    assert (game_dir / "mods/a.jar").read_bytes() == b"a"
    assert (game_dir / "mods/b.jar").read_bytes() == b"b"
    assert not (game_dir / "mods/new.jar").exists()
    assert load_sync_receipt(launcher.paths, created.instance_id) == previous
    assert not (game_dir / ".nostalgia-sync-pending.json").exists()


def test_host_identity_persists_but_reused_registration_gets_new_identity(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path)
    launcher.create_instance(Instance("host", "1.20.1"))
    previous = ensure_sync_pack_id(launcher.paths, "host")
    assert ensure_sync_pack_id(launcher.paths, "host") == previous
    unregister_instance(launcher.paths, "host")
    launcher.create_instance(Instance("host", "1.20.1"))
    assert ensure_sync_pack_id(launcher.paths, "host") != previous
