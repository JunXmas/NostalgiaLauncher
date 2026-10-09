"""Xóa hẳn đúng bản chơi, giữ thư mục ngoài và bản chơi lân cận."""

from dataclasses import replace
from pathlib import Path

import pytest
from test_backups_trash import prepared

from nostalgia.api import Instance
from nostalgia.errors import InstanceError


@pytest.mark.parametrize("external", [False, True])
def test_delete_permanently_removes_the_owned_folder_only(tmp_path: Path, external: bool) -> None:
    launcher = prepared(tmp_path, external=external)
    launcher.save_instance(Instance("other", "1.21"))
    launcher.delete_instance("survival")
    assert not launcher.paths.instance_dir("survival").exists()
    assert [instance.instance_id for instance in launcher.list_instances()] == ["other"]
    assert not launcher.list_trashed_instances()
    if external:
        assert (tmp_path / "other-drive/saves/Thế giới/level.dat").read_bytes() == b"world-v1"


def test_purge_old_trash_removes_the_world_without_touching_a_new_instance(tmp_path: Path) -> None:
    launcher = prepared(tmp_path)
    trash_id = launcher.trash_instance("survival")
    launcher.save_instance(Instance("survival", "1.21"))
    launcher.remove_trashed_instance(trash_id)
    assert not (launcher.paths.data_dir / "trash" / trash_id).exists()
    assert not launcher.list_trashed_instances()
    assert launcher.list_instances()[0].version_id == "1.21"
    with pytest.raises(InstanceError):
        launcher.remove_trashed_instance("../survival")


def test_explicit_external_delete_removes_all_files_and_registration(tmp_path: Path) -> None:
    launcher = prepared(tmp_path, external=True)
    launcher.delete_instance("survival", delete_external=True)
    assert not launcher.list_instances()
    assert not (tmp_path / "other-drive").exists()


def test_external_delete_refuses_shared_and_launcher_directories(tmp_path: Path) -> None:
    launcher = prepared(tmp_path, external=True)
    launcher.save_instance(
        Instance(
            "other",
            "1.21",
            game_dir_override=str(tmp_path / "other-drive/child"),
        )
    )
    with pytest.raises(InstanceError, match="bản chơi khác"):
        launcher.delete_instance("survival", delete_external=True)
    assert (tmp_path / "other-drive/saves/Thế giới/level.dat").read_bytes() == b"world-v1"
    assert launcher.paths.instance_json("survival").exists()
    original = next(
        instance for instance in launcher.list_instances() if instance.instance_id == "survival"
    )
    launcher.save_instance(replace(original, game_dir_override=str(launcher.paths.data_dir)))
    with pytest.raises(InstanceError, match="kho launcher"):
        launcher.delete_instance("survival", delete_external=True)
    assert launcher.paths.instance_json("other").exists()


def test_delete_and_purge_do_not_follow_registry_symlinks(tmp_path: Path) -> None:
    launcher = prepared(tmp_path)
    source = launcher.paths.instance_dir("survival")
    external = tmp_path / "external"
    source.rename(external)
    try:
        source.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("hệ điều hành không cho tạo symlink")
    with pytest.raises(InstanceError, match="liên kết"):
        launcher.delete_instance("survival")
    assert (external / "instance.json").exists()
    trash_dir = launcher.paths.data_dir / "trash"
    trash_dir.mkdir()
    (trash_dir / "linked").symlink_to(external, target_is_directory=True)
    with pytest.raises(InstanceError):
        launcher.remove_trashed_instance("linked")
    assert (external / "saves/Thế giới/level.dat").read_bytes() == b"world-v1"
