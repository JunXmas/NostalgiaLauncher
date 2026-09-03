"""Cấu hình chung cho test.

Tấm lưới an toàn quan trọng nhất của kho này: mọi test đều chạy với HOME và toàn bộ
biến môi trường đường dẫn trỏ vào thư mục tạm. Kho tiền nhiệm (NostalgiaLauncher) từng
ghi đè ~/.config/... trong lúc chạy test và làm mất sạch instance của người dùng — lỗi
đó không được phép lặp lại ở đây.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Mọi biến môi trường có thể dẫn code về dữ liệu thật của người dùng.
PATH_ENV_VARS = (
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "XDG_DATA_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "MCCORE_DATA_DIR",
)


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch) -> Path:
    """Ép mọi đường dẫn của test vào tmp_path. Tự động áp cho mọi test, không cần khai."""
    home = tmp_path / "home"
    home.mkdir()
    for name in PATH_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    monkeypatch.setenv("MCCORE_DATA_DIR", str(tmp_path / "data"))
    return home
