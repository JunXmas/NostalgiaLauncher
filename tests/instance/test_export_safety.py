"""Xuất thất bại không làm hỏng file đích, không đi theo liên kết hoặc lẫn dữ liệu."""

import zipfile
from pathlib import Path
from typing import Any, Literal
from unittest.mock import patch

import pytest

from export_fixture import prepared_export
from nostalgia.errors import InstanceError


def test_existing_export_survives_failure_and_temporary_files_are_removed(tmp_path: Path) -> None:
    launcher = prepared_export(tmp_path)
    target = tmp_path / "pack.mrpack"
    target.write_bytes(b"previous export")
    with pytest.raises(InstanceError, match="đã tồn tại"):
        launcher.export_instance_modpack("custom", target, "mrpack")
    with (
        patch.object(zipfile.ZipFile, "open", side_effect=OSError("disk full")),
        pytest.raises(InstanceError, match="không xuất"),
    ):
        launcher.export_instance_modpack("custom", target, "mrpack", overwrite=True)
    assert target.read_bytes() == b"previous export"
    assert not list(tmp_path.glob(".modpack-*"))


@pytest.mark.parametrize("link_directory", [False, True])
def test_export_never_reads_a_symlink_to_private_files(
    tmp_path: Path, link_directory: bool
) -> None:
    launcher = prepared_export(tmp_path)
    private = tmp_path / "private"
    private.mkdir()
    (private / "secret.txt").write_bytes(b"secret")
    mods = launcher.paths.instance_dir("custom") / "mods"
    target = mods / ("linked" if link_directory else "linked.jar")
    try:
        target.symlink_to(
            private if link_directory else private / "secret.txt",
            target_is_directory=link_directory,
        )
    except OSError:
        pytest.skip("hệ điều hành không cho tạo symlink")
    archive = tmp_path / "pack.zip"
    with pytest.raises(InstanceError, match="liên kết"):
        launcher.export_instance_modpack("custom", archive, "zip")
    assert not archive.exists()
    assert (private / "secret.txt").read_bytes() == b"secret"


def test_export_refuses_its_own_game_directory_and_case_collisions(tmp_path: Path) -> None:
    launcher = prepared_export(tmp_path)
    game_dir = launcher.paths.instance_dir("custom")
    with pytest.raises(InstanceError, match="bên ngoài"):
        launcher.export_instance_modpack("custom", game_dir / "pack.zip", "zip")
    (game_dir / "config/CLIENT.toml").write_bytes(b"other")
    with pytest.raises(InstanceError, match="trùng nhau"):
        launcher.export_instance_modpack("custom", tmp_path / "pack.zip", "zip")


def test_export_fails_when_files_change_during_compression(tmp_path: Path) -> None:
    launcher = prepared_export(tmp_path)
    target = tmp_path / "pack.zip"
    target.write_bytes(b"previous")
    write_member = zipfile.ZipFile.open
    changed = False

    def changing_open(
        archive: zipfile.ZipFile,
        filename: str | zipfile.ZipInfo,
        mode: Literal["r", "w"] = "r",
        **kwargs: Any,
    ) -> Any:
        nonlocal changed
        if mode == "w" and not changed:
            changed = True
            (launcher.paths.instance_dir("custom") / "mods/local.jar").write_bytes(b"changed")
        return write_member(archive, filename, mode, **kwargs)

    with (
        patch.object(zipfile.ZipFile, "open", changing_open),
        pytest.raises(InstanceError, match="thay đổi"),
    ):
        launcher.export_instance_modpack("custom", target, "zip", overwrite=True)
    assert target.read_bytes() == b"previous"
    assert not list(tmp_path.glob(".modpack-*"))
