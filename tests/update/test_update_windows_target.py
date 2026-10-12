"""Windows thiếu quyền ghi phải chọn bộ cài Windows, không chạy trình quản lý gói Linux."""

import sys
from pathlib import Path

import pytest

from nostalgia.api import Launcher
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.update import apply
from nostalgia.update.release import LauncherRelease, ReleaseAsset


def _windows_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writable: bool) -> None:
    executable = tmp_path / "Nostalgia Launcher" / "nostalgia-ui.exe"
    executable.parent.mkdir()
    executable.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(apply, "_dir_is_writable", lambda _directory: writable)


def test_protected_windows_install_selects_setup_instead_of_deb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tái hiện báo lỗi pkexec của người chơi Windows: cùng release có đủ gói cả hai hệ."""
    _windows_install(tmp_path, monkeypatch, writable=False)
    launcher = Launcher(
        paths=DataPaths(tmp_path / "data", tmp_path / "config"),
        platform=Platform(os_name="windows", os_arch="x64", os_version="10"),
    )
    names = (
        "nostalgia_9.9.9_amd64.deb",
        "nostalgia-9.9.9-linux-x64.AppImage",
        "nostalgia-9.9.9-windows-x64.zip",
        "nostalgia-9.9.9-windows-x64-setup.exe",
    )
    release = LauncherRelease(
        "9.9.9",
        "",
        "https://example.invalid/release",
        tuple(
            ReleaseAsset(asset_name, "https://example.invalid/" + asset_name, 1)
            for asset_name in names
        ),
    )

    release_asset = launcher.launcher_update_asset(release)

    assert release_asset is not None
    assert release_asset.name == "nostalgia-9.9.9-windows-x64-setup.exe"
    assert launcher.launcher_install_kind() == "windows-installer"


def test_windows_ignores_appimage_environment_and_keeps_writable_zip_updates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _windows_install(tmp_path, monkeypatch, writable=True)
    monkeypatch.setenv("APPIMAGE", "/tmp/unrelated.AppImage")

    assert apply.detect_install_kind() == apply.INSTALL_KIND_FROZEN


def test_protected_windows_install_never_falls_back_to_an_unusable_zip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _windows_install(tmp_path, monkeypatch, writable=False)
    launcher = Launcher(
        paths=DataPaths(tmp_path / "data", tmp_path / "config"),
        platform=Platform(os_name="windows", os_arch="x64", os_version="10"),
    )
    release = LauncherRelease(
        "9.9.9", "", "", (ReleaseAsset("nostalgia-9.9.9-windows-x64.zip", "https://x/zip", 1),)
    )

    assert launcher.launcher_update_asset(release) is None
