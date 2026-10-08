"""Từ chối đường dẫn/icon độc hại, phục hồi journal và tránh mục tiêu cập nhật mơ hồ."""

import base64
import json
import shutil
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest
from test_sync_updates import UpdateGateway, sync
from test_sync_updates import update_rig as update_rig

from nostalgia.api import Instance, Launcher
from nostalgia.content.sync_icon import archive_icon, safe_sync_icon
from nostalgia.errors import Cancelled, MultiplayerError
from nostalgia.instance.store import load_instance
from nostalgia.instance.sync_receipt import RECEIPT_FILE
from nostalgia.instance.sync_transaction import recover_sync_update, sync_transaction
from nostalgia.multiplayer.sync_manifest import manifest_document, parse_sync_manifest
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import atomic_write_json
from nostalgia.storage.sync_lock import sync_lock

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1sAAAAASUVORK5CYII="
)


def test_bounded_private_icon_and_manifest_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "mod.jar"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "fabric.mod.json", json.dumps({"id": "a", "name": "Private", "icon": "assets/a.png"})
        )
        archive.writestr("assets/a.png", PNG)
    icon = archive_icon(path)
    assert icon.startswith("data:image/png;base64,") and safe_sync_icon(icon) == icon
    gateway = UpdateGateway({"mods/a.jar": path.read_bytes()})
    manifest = replace(
        gateway.manifest,
        files=(replace(gateway.manifest.files[0], title="Private", icon_url=icon),),
    )
    assert parse_sync_manifest(manifest_document(manifest)) == manifest
    for address in [
        "file:///etc/passwd",
        "http://127.0.0.1/a.png",
        "https://attacker.invalid/a.png",
        "data:image/svg+xml,<svg/>",
        "data:image/png;base64," + "A" * 23000,
    ]:
        assert not safe_sync_icon(address)
        with pytest.raises(MultiplayerError):
            parse_sync_manifest(
                manifest_document(
                    replace(manifest, files=(replace(manifest.files[0], icon_url=address),))
                )
            )
    with pytest.raises(MultiplayerError):
        parse_sync_manifest(
            manifest_document(
                replace(
                    manifest,
                    files=(
                        *manifest.files,
                        replace(manifest.files[0], relative_path="mods/a.jar.disabled"),
                    ),
                )
            )
        )


def test_duplicate_identity_refuses_instead_of_guessing(
    update_rig: tuple[Launcher, UpdateGateway],
) -> None:
    launcher, gateway = update_rig
    first = sync(launcher, gateway)
    second = launcher.create_instance(Instance("second", "1.20.1"))
    receipt_path = launcher.paths.instance_dir(first.instance_id) / RECEIPT_FILE
    fields = json.loads(receipt_path.read_text())
    fields["instance_id"] = second.instance_id
    atomic_write_json(launcher.paths.instance_dir(second.instance_id) / RECEIPT_FILE, fields)
    with pytest.raises(MultiplayerError, match="nhiều"):
        sync(launcher, gateway)


def test_symlink_and_cancelled_download_cannot_damage_previous_instance(
    update_rig: tuple[Launcher, UpdateGateway], tmp_path: Path
) -> None:
    launcher, gateway = update_rig
    created = sync(launcher, gateway)
    game_dir = launcher.instance_game_dir(created)
    external = tmp_path / "outside"
    external.mkdir()
    (external / "a.jar").write_bytes(b"outside")
    shutil.rmtree(game_dir / "mods")
    (game_dir / "mods").symlink_to(external, target_is_directory=True)
    with pytest.raises(MultiplayerError, match="symlink"):
        sync(launcher, gateway)
    assert (external / "a.jar").read_bytes() == b"outside"
    (game_dir / "mods").unlink()
    (game_dir / "mods").mkdir()
    (game_dir / "mods/a.jar").write_bytes(b"a")
    gateway.replace_payloads({"mods/a.jar": b"changed"})
    cancel_token = CancelToken()

    def stop_transfer(_room_code: str, _sync_file: object) -> bytes:
        cancel_token.cancel()
        return b"changed"

    with (
        patch.object(gateway, "download", side_effect=stop_transfer),
        pytest.raises(Cancelled),
    ):
        launcher.sync_room_modpack(gateway, "fixture", gateway.manifest, cancel_token=cancel_token)
    assert (game_dir / "mods/a.jar").read_bytes() == b"a"


def test_pending_journal_blocks_play_then_recovers_and_lock_excludes_other_writer(
    update_rig: tuple[Launcher, UpdateGateway],
) -> None:
    launcher, gateway = update_rig
    created = sync(launcher, gateway)
    game_dir = launcher.instance_game_dir(created)
    with sync_lock(game_dir), pytest.raises(MultiplayerError, match="khác"), sync_lock(game_dir):
        pytest.fail("second writer accepted")
    with (
        patch(
            "nostalgia.instance.sync_transaction.recover_sync_update",
            side_effect=OSError("interrupted"),
        ),
        pytest.raises(OSError),
        sync_transaction(game_dir, game_dir, frozenset({"mods/a.jar"})),
    ):
        (game_dir / "mods/a.jar").write_bytes(b"half applied")
        raise OSError("crash")
    assert load_instance(launcher.paths, created.instance_id).instance_id == created.instance_id
    recover_sync_update(game_dir, game_dir)
    assert (game_dir / "mods/a.jar").read_bytes() == b"a"
    assert load_instance(launcher.paths, created.instance_id).instance_id == created.instance_id
