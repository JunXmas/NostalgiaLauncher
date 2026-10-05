"""Cài bản mới bằng gói của hệ thống: thay file AppImage, và gọi `pkexec` cho `.deb`/`.rpm`.

Vì sao đáng có: đây là đường duy nhất để bản AppImage và bản `.deb`/`.rpm` tự lên bản mới.
Hỏng lặng lẽ (thiếu cờ chạy, nuốt lỗi khi người dùng bấm Huỷ) thì người dùng tưởng đã cập
nhật trong khi vẫn đang chạy bản cũ.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from nostalgia.errors import UpdateError
from nostalgia.update.packages import (
    appimage_path,
    install_system_package,
    replace_appimage,
)


def test_replacing_an_appimage_keeps_it_runnable(tmp_path: Path) -> None:
    target = tmp_path / "Nostalgia.AppImage"
    target.write_bytes(b"cu")
    downloaded = tmp_path / "moi.AppImage"
    downloaded.write_bytes(b"moi")

    replace_appimage(downloaded, target)

    assert target.read_bytes() == b"moi"
    # Không có cờ chạy thì người dùng bấm đúp ra một hộp thoại lỗi, không phải launcher.
    assert target.stat().st_mode & stat.S_IXUSR
    assert not (tmp_path / "Nostalgia.AppImage.new").exists()


def test_replacing_an_appimage_in_a_readonly_folder_says_so(tmp_path: Path) -> None:
    folder = tmp_path / "chi-doc"
    folder.mkdir()
    target = folder / "Nostalgia.AppImage"
    target.write_bytes(b"cu")
    folder.chmod(0o500)
    try:
        with pytest.raises(UpdateError, match="không ghi được"):
            replace_appimage(target, target)
    finally:
        folder.chmod(0o700)


def test_appimage_path_follows_the_runtime_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APPIMAGE", raising=False)
    assert appimage_path() is None
    monkeypatch.setenv("APPIMAGE", "/home/ai/Nostalgia.AppImage")
    assert appimage_path() == Path("/home/ai/Nostalgia.AppImage")


def _fake_tool(directory: Path, name: str, script: str) -> None:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
    path.chmod(0o755)


def test_installing_a_deb_goes_through_pkexec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log = tmp_path / "log.txt"
    _fake_tool(fake_bin, "pkexec", f'echo "$@" > {log}')
    _fake_tool(fake_bin, "apt-get", "exit 0")
    monkeypatch.setenv("PATH", str(fake_bin), prepend=os.pathsep)
    package = tmp_path / "nostalgia_1.0.15_amd64.deb"
    package.write_bytes(b"deb")

    install_system_package(package)

    assert log.read_text().split() == ["apt-get", "install", "-y", str(package)]


def test_user_cancelling_the_password_dialog_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _fake_tool(fake_bin, "pkexec", "exit 126")
    _fake_tool(fake_bin, "apt-get", "exit 0")
    monkeypatch.setenv("PATH", str(fake_bin), prepend=os.pathsep)
    package = tmp_path / "nostalgia_1.0.15_amd64.deb"
    package.write_bytes(b"deb")

    with pytest.raises(UpdateError, match="huỷ"):
        install_system_package(package)


def test_a_machine_without_pkexec_says_so_instead_of_trying_sudo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    empty = tmp_path / "bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    package = tmp_path / "nostalgia_1.0.15_amd64.deb"
    package.write_bytes(b"deb")

    with pytest.raises(UpdateError, match="pkexec"):
        install_system_package(package)


def test_an_unknown_package_kind_is_refused(tmp_path: Path) -> None:
    package = tmp_path / "nostalgia.pkg.tar.zst"
    package.write_bytes(b"?")
    with pytest.raises(UpdateError, match="không biết cách cài"):
        install_system_package(package)
