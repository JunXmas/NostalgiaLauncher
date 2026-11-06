"""Chuyển drive/UNC tại biên I/O, giữ nguyên đường dẫn trên hệ khác."""

from pathlib import Path

import pytest

from nostalgia.storage.windows_path import extended_windows_path


@pytest.mark.parametrize(
    ("spelling", "expected"),
    [
        (r"C:\cache\stage\file.json", r"\\?\C:\cache\stage\file.json"),
        (r"C:\cache\folder\..\file.json", r"\\?\C:\cache\file.json"),
        (r"\\server\share\stage\file.json", r"\\?\UNC\server\share\stage\file.json"),
        (r"\\?\C:\cache\file.json", r"\\?\C:\cache\file.json"),
        (r"\\?\UNC\server\share\file.json", r"\\?\UNC\server\share\file.json"),
    ],
)
def test_windows_extended_drive_unc_and_normalization(spelling: str, expected: str) -> None:
    path = extended_windows_path(Path(spelling), platform_name="win32")
    assert str(path) == expected
    assert extended_windows_path(path, platform_name="win32") == path


@pytest.mark.parametrize("platform_name", ["linux", "darwin"])
def test_non_windows_paths_are_unchanged(platform_name: str) -> None:
    path = Path("relative/cache/file.json")
    assert extended_windows_path(path, platform_name=platform_name) is path
