"""Đường dẫn I/O Win32 mở rộng, không phụ thuộc LongPathsEnabled của máy người chơi."""

import ntpath
import sys
from pathlib import Path


def extended_windows_path(path: Path, *, platform_name: str | None = None) -> Path:
    """Chỉ dùng tại biên I/O; metadata, đối số game và đường dẫn hiển thị giữ dạng thường."""
    if (sys.platform if platform_name is None else platform_name) != "win32":
        return path
    spelling = ntpath.abspath(path)
    if spelling.startswith("\\\\?\\"):
        return Path(spelling)
    if spelling.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + spelling[2:])
    return Path("\\\\?\\" + spelling)
