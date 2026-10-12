"""Mở bộ cài Windows đã kiểm SHA-256 qua hộp thoại UAC của hệ điều hành."""

from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from nostalgia.errors import UpdateError


def start_windows_installer(package_path: Path, install_dir: Path) -> None:
    """Xin quyền trước khi thoát launcher; huỷ UAC thì launcher hiện tại vẫn chạy.

    Inno hỗ trợ /ALLUSERS để cài đè bản toàn máy và /DIR để giữ đúng nơi đã cài.
    Không dùng chế độ im lặng: người chơi hoàn tất wizard, rồi mở bản mới ở bước cuối.
    Shell không kế thừa cwd của launcher để tránh khoá thư mục cần cập nhật.
    """
    os_platform = sys.platform
    if os_platform != "win32":
        raise UpdateError("The Windows installer can only run on Windows.")
    if package_path.suffix.lower() != ".exe" or not package_path.is_file():
        raise UpdateError("The downloaded update is not a Windows installer.")
    startfile: Callable[..., None] | None = getattr(os, "startfile", None)
    if startfile is None:
        raise UpdateError("Windows could not open the update installer.")
    try:
        startfile(
            str(package_path),
            "runas",
            f'/ALLUSERS /DIR="{install_dir}"',
            tempfile.gettempdir(),
            1,
        )
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1223:
            raise UpdateError(
                "Windows update cancelled. The current launcher is still running."
            ) from exc
        raise UpdateError(f"Could not open the Windows installer: {exc}") from exc
