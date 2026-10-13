"""Player data, custom mods and prior files survive updates and failed writes."""

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from builtin_update_fixture import Upgrade, jar
from builtin_update_fixture import upgrade as upgrade
from nostalgia.content.builtin_receipt import (
    RECEIPT_FILE,
    BuiltinReceipt,
    BundledFile,
    load_builtin_receipt,
)
from nostalgia.content.builtin_update import plan_builtin_update
from nostalgia.errors import Cancelled, ContentError, NetworkError
from nostalgia.facade import preset_updates
from nostalgia.instance.store import load_instance
from nostalgia.instance.sync_transaction import replace_sync_bytes
from nostalgia.operations.cancellation import CancelToken


def snapshot(game_dir: Path) -> dict[str, bytes]:
    return {
        p.relative_to(game_dir).as_posix(): p.read_bytes()
        for p in game_dir.rglob("*")
        if p.is_file()
        and ".nostalgia-sync-backups" not in p.parts
        and p.name != ".nostalgia-sync.lock"
    }


@pytest.mark.parametrize("external", [False, True])
def test_upgrade_preserves_player_data_and_instance(
    upgrade: Upgrade, tmp_path: Path, external: bool
) -> None:
    launcher, instance, host, state = upgrade
    original_dir = launcher.instance_game_dir(instance)
    if external:
        import shutil

        game_dir = tmp_path / "custom-game"
        shutil.copytree(original_dir, game_dir)
        instance = replace(instance, game_dir_override=str(game_dir))
    else:
        game_dir = original_dir
    instance = replace(
        instance,
        display_name="Dây chuyền của tôi",
        max_heap_megabytes=6144,
        group_name="Industrial",
        favorite=True,
    )
    launcher.save_instance(instance)
    protected = {
        "saves/factory/level.dat": b"world",
        "saves/factory/playerdata/player.dat": b"player",
        "options.txt": b"custom controls",
        "servers.dat": b"custom servers",
        "config/player.toml": b"my settings",
        "mods/personal.jar": jar("personal"),
        "shaderpacks/mine.zip": b"shader",
        "resourcepacks/mine.zip": b"textures",
        "screenshots/factory.png": b"photo",
    }
    for name, payload in protected.items():
        destination = game_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    (game_dir / "config/new.toml").unlink()
    base_requests = state.request_count("/update/base.jar")
    result = launcher.update_builtin_modpack(instance.instance_id, allowed_hosts=(host,))
    assert result == instance == load_instance(launcher.paths, instance.instance_id)
    assert state.request_count("/update/base.jar") == base_requests
    assert (game_dir / "mods/jei.jar").read_bytes() == jar("jei")
    assert (game_dir / "mods/mezz_config.jar").read_bytes() == jar("mezz_config")
    assert (game_dir / "config/new.toml").read_text() == "new default"
    assert all((game_dir / name).read_bytes() == payload for name, payload in protected.items())
    status = launcher.builtin_pack_status(result)
    assert status is not None and not status.update_available
    receipt = load_builtin_receipt(launcher.paths.instance_dir(instance.instance_id))
    assert receipt is not None and receipt.version_id == "1.0.2"


@pytest.mark.parametrize("disabled", [False, True])
def test_deleted_or_disabled_mod_is_not_reinstalled(upgrade: Upgrade, disabled: bool) -> None:
    launcher, instance, host, state = upgrade
    game_dir = launcher.instance_game_dir(instance)
    mod = game_dir / "mods/base.jar"
    if disabled:
        mod.rename(mod.with_suffix(".jar.disabled"))
    else:
        mod.unlink()
    before = state.request_count("/update/base.jar")
    launcher.update_builtin_modpack(instance.instance_id, allowed_hosts=(host,))
    assert not mod.exists()
    assert (game_dir / "mods/base.jar.disabled").exists() == disabled
    assert state.request_count("/update/base.jar") == before


@pytest.mark.parametrize("conflict", ["changed-managed", "user-filename", "user-mod-id"])
def test_user_mod_conflicts_leave_all_existing_files_intact(
    upgrade: Upgrade, conflict: str
) -> None:
    launcher, instance, host, _ = upgrade
    game_dir = launcher.instance_game_dir(instance)
    name, payload = {
        "changed-managed": ("base.jar", jar("base", "custom")),
        "user-filename": ("jei.jar", jar("jei", "custom")),
        "user-mod-id": ("my-jei.jar", jar("jei", "custom")),
    }[conflict]
    (game_dir / "mods" / name).write_bytes(payload)
    before = snapshot(game_dir)
    with pytest.raises(ContentError):
        launcher.update_builtin_modpack(instance.instance_id, allowed_hosts=(host,))
    assert snapshot(game_dir) == before


def test_missing_download_leaves_old_pack_intact(upgrade: Upgrade) -> None:
    launcher, instance, host, state = upgrade
    game_dir = launcher.instance_game_dir(instance)
    state.add("/update/jei.jar", b"bad digest")
    before = snapshot(game_dir)
    with pytest.raises(NetworkError):
        launcher.update_builtin_modpack(instance.instance_id, allowed_hosts=(host,))
    assert snapshot(game_dir) == before


@pytest.mark.parametrize("request_cancellation", [False, True])
def test_interrupted_commit_rolls_back_mods_and_receipt(
    upgrade: Upgrade, monkeypatch: pytest.MonkeyPatch, request_cancellation: bool
) -> None:
    launcher, instance, host, _ = upgrade
    game_dir = launcher.instance_game_dir(instance)
    before = snapshot(game_dir)
    actual = replace_sync_bytes
    cancel_request = CancelToken()

    def interrupt(source: Path, destination: Path) -> None:
        actual(source, destination)
        if request_cancellation:
            cancel_request.cancel()
        else:
            raise OSError("simulated disk failure after first write")

    monkeypatch.setattr(preset_updates, "replace_sync_bytes", interrupt)
    with pytest.raises(Cancelled if request_cancellation else OSError):
        launcher.update_builtin_modpack(
            instance.instance_id, allowed_hosts=(host,), cancel_token=cancel_request
        )
    assert snapshot(game_dir) == before
    assert not (game_dir / ".nostalgia-sync-pending.json").exists()
    assert (game_dir / ".nostalgia-sync-backups").is_dir()


def test_rc35_marker_is_migrated_without_recreating_instance(
    upgrade: Upgrade, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, instance, host, _ = upgrade
    registry = launcher.paths.instance_dir(instance.instance_id)
    legacy = load_builtin_receipt(registry)
    assert legacy is not None
    (registry / RECEIPT_FILE).unlink()
    monkeypatch.setattr(preset_updates, "legacy_receipt", lambda: legacy)
    status = launcher.builtin_pack_status(instance)
    assert status is not None and status.update_available
    assert launcher.update_builtin_modpack(instance.instance_id, allowed_hosts=(host,)) == instance
    receipt = load_builtin_receipt(registry)
    assert receipt is not None and receipt.version_id == "1.0.2"


def test_only_verified_managed_artifact_is_replaced(tmp_path: Path) -> None:
    game_dir, stage = tmp_path / "game", tmp_path / "stage"
    for p in (game_dir / "mods", stage / "mods"):
        p.mkdir(parents=True)
    old, new = jar("base", "1"), jar("base", "2")
    (game_dir / "mods/base-1.jar.disabled").write_bytes(old)
    (stage / "mods/base-2.jar").write_bytes(new)

    def bundled_file(payload: bytes) -> BundledFile:
        return BundledFile(hashlib.sha1(payload).hexdigest(), "project:base")

    changes = plan_builtin_update(
        game_dir,
        stage,
        BuiltinReceipt("1", {"mods/base-1.jar": bundled_file(old)}),
        BuiltinReceipt("2", {"mods/base-2.jar": bundled_file(new)}),
    )
    assert changes.copies == {"mods/base-2.jar.disabled": "mods/base-2.jar"}
    assert changes.removals == frozenset({"mods/base-1.jar.disabled"})
