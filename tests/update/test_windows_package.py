"""Bộ cài Windows phải xin quyền đúng cách, giữ thư mục cài và không nuốt việc huỷ UAC."""

import os
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from nostalgia.errors import UpdateError
from nostalgia.update.packages import install_system_package
from nostalgia.update.windows_package import start_windows_installer


def test_native_installer_requests_uac_and_keeps_the_existing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "nostalgia-windows-setup.exe"
    package.touch()
    install_dir = tmp_path / "Nostalgia thử ứ"
    native_shell = Mock()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "startfile", native_shell, raising=False)

    start_windows_installer(package, install_dir)

    arguments = native_shell.call_args.args
    assert arguments[:3] == (str(package), "runas", f'/ALLUSERS /DIR="{install_dir}"')
    assert Path(arguments[3]).is_dir() and Path(arguments[3]) != install_dir
    assert arguments[4] == 1


def test_cancelling_uac_does_not_report_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "setup.exe"
    package.touch()
    failure = OSError("UAC cancelled")
    failure.winerror = 1223  # type: ignore[attr-defined]
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "startfile", Mock(side_effect=failure), raising=False)

    with pytest.raises(UpdateError, match=r"cancelled.*still running"):
        start_windows_installer(package, tmp_path / "install")


@pytest.mark.parametrize("asset_name", ["setup.deb", "setup.rpm", "missing.exe"])
def test_invalid_or_missing_installer_never_reaches_the_windows_shell(
    asset_name: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / asset_name
    if not asset_name.startswith("missing"):
        package.touch()
    native_shell = Mock()
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "startfile", native_shell, raising=False)

    with pytest.raises(UpdateError, match="not a Windows installer"):
        start_windows_installer(package, tmp_path / "install")

    native_shell.assert_not_called()


def test_windows_never_runs_pkexec_even_with_a_previously_downloaded_deb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(UpdateError, match=r"only.*Linux"):
        install_system_package(tmp_path / "old-update.deb")


def test_windows_installer_is_refused_on_linux(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(UpdateError, match=r"only.*Windows"):
        start_windows_installer(tmp_path / "setup.exe", tmp_path / "install")
