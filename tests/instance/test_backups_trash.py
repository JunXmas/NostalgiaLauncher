"""Dữ liệu thế giới còn nguyên qua sao lưu, phục hồi và thùng rác; ZIP lạ bị chặn."""

from __future__ import annotations

import json
import stat
import zipfile
from pathlib import Path

import pytest

from nostalgia.api import Launcher
from nostalgia.errors import InstanceError
from nostalgia.instance.model import Instance


def prepared(tmp_path: Path, *, external: bool = False) -> Launcher:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    instance = Instance(
        "survival",
        "1.20.1",
        display_name="Sinh tồn",
        game_dir_override=str(tmp_path / "other-drive") if external else "",
        group_name="Modpack",
        favorite=True,
    )
    launcher.save_instance(instance)
    folder = launcher.instance_game_dir(instance)
    (folder / "saves" / "Thế giới").mkdir(parents=True)
    (folder / "saves" / "Thế giới" / "level.dat").write_bytes(b"world-v1")
    return launcher


@pytest.mark.parametrize("external", [False, True])
def test_backup_restores_to_new_instance_without_overwriting_world(
    tmp_path: Path, external: bool
) -> None:
    launcher = prepared(tmp_path, external=external)
    original = launcher.list_instances()[0]
    world = launcher.instance_game_dir(original) / "saves" / "Thế giới" / "level.dat"
    backup = launcher.backup_instance("survival")
    world.write_bytes(b"world-v2")
    restored = launcher.restore_instance_backup(backup.path, "restored")
    assert restored.instance_id == "restored" and restored.version_id == "1.20.1"
    assert restored.favorite and restored.group_name == "Modpack"
    assert not restored.game_dir_override
    assert (
        launcher.instance_game_dir(restored) / "saves" / "Thế giới" / "level.dat"
    ).read_bytes() == b"world-v1"
    assert world.read_bytes() == b"world-v2"
    with pytest.raises(InstanceError, match="đã có"):
        launcher.restore_instance_backup(backup.path, "survival")
    assert world.read_bytes() == b"world-v2"


@pytest.mark.parametrize("external", [False, True])
def test_trash_restore_handles_reused_id_and_preserves_external_folder(
    tmp_path: Path, external: bool
) -> None:
    launcher = prepared(tmp_path, external=external)
    original = launcher.list_instances()[0]
    world = launcher.instance_game_dir(original) / "saves" / "Thế giới" / "level.dat"
    trash_id = launcher.trash_instance("survival")
    assert not launcher.list_instances()
    assert len(launcher.list_trashed_instances()) == 1
    if external:
        assert world.read_bytes() == b"world-v1"
    launcher.save_instance(Instance("survival", "1.21"))
    restored = launcher.restore_trashed_instance(trash_id)
    assert restored.instance_id == "survival-restore-2"
    assert (
        launcher.instance_game_dir(restored) / "saves" / "Thế giới" / "level.dat"
    ).read_bytes() == b"world-v1"
    assert {i.version_id for i in launcher.list_instances()} == {"1.20.1", "1.21"}
    assert not launcher.list_trashed_instances()


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "game/../../escape",
        "/escape",
        "game/C:/x",
        "game\\escape",
        "game/instance.json",
    ],
)
def test_malicious_backup_never_writes_outside_staging(tmp_path: Path, name: str) -> None:
    launcher = prepared(tmp_path)
    backup = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(backup, "w") as archive:
        archive.writestr(
            "manifest.json", json.dumps({"format": 1, "instance": {"version_id": "1.20.1"}})
        )
        archive.writestr(name, "malicious")
    with pytest.raises(InstanceError):
        launcher.restore_instance_backup(backup, "restored")
    assert not launcher.paths.instance_dir("restored").exists()
    assert not (tmp_path / "escape").exists()
    assert [i.instance_id for i in launcher.list_instances()] == ["survival"]


def test_backup_symlink_and_case_collision_are_rejected(tmp_path: Path) -> None:
    launcher = prepared(tmp_path)
    for symlink in [False, True]:
        backup = tmp_path / "unsafe.zip"
        with zipfile.ZipFile(backup, "w") as archive:
            archive.writestr(
                "manifest.json", json.dumps({"format": 1, "instance": {"version_id": "1.20.1"}})
            )
            if symlink:
                zip_entry = zipfile.ZipInfo("game/link")
                zip_entry.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(zip_entry, "/outside")
            else:
                archive.writestr("game/Options.txt", "first")
                archive.writestr("game/options.txt", "second")
        with pytest.raises(InstanceError):
            launcher.restore_instance_backup(backup, "restored")
        assert not launcher.paths.instance_dir("restored").exists()


def test_broken_trash_entry_does_not_hide_valid_instances(tmp_path: Path) -> None:
    launcher = prepared(tmp_path)
    trash_id = launcher.trash_instance("survival")
    broken = launcher.paths.data_dir / "trash" / "broken"
    broken.mkdir()
    (broken / "instance.json").write_text("not json")
    assert [i.trash_id for i in launcher.list_trashed_instances()] == [trash_id]


def test_missing_game_folder_fails_instead_of_creating_empty_backup(tmp_path: Path) -> None:
    import shutil

    launcher = prepared(tmp_path, external=True)
    shutil.rmtree(tmp_path / "other-drive")
    with pytest.raises(InstanceError):
        launcher.backup_instance("survival")
    assert not launcher.list_instance_backups()
