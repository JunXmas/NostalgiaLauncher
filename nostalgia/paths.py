"""Tên chương trình và các thư mục dữ liệu, kèm chuyển đổi từ tên cũ.

Dự án từng mang tên `mc-launcher`. Đổi tên mà bỏ mặc dữ liệu cũ thì người dùng
mất tài khoản đã đăng nhập và cấu hình, nên chỗ này lo việc dời sang tên mới.

Mỗi hệ điều hành có quy ước riêng về chỗ để cấu hình và cache. Chiều theo quy ước
sở tại không phải để cho đẹp: trên Windows chỉ %APPDATA% mới theo người dùng qua
roaming profile, còn trên macOS thư mục chấm ở home bị Finder giấu và bị Time
Machine đối xử khác. Đặt sai chỗ thì người dùng không tìm thấy file của mình.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Nostalgia Launcher"
APP_SLUG = "nostalgia-launcher"
APP_VERSION = "0.2"

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"


def _env_dir(name: str) -> Path | None:
    """Đọc biến môi trường chỉ chỗ, bỏ qua nếu trống hoặc là đường dẫn tương đối."""
    value = os.environ.get(name)
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else None


def _dirs() -> tuple[Path, Path, Path]:
    """Trả về (config, cache, game) theo quy ước của hệ điều hành đang chạy."""
    home = Path.home()
    if WINDOWS:
        # %APPDATA% roaming theo tài khoản; cache là dữ liệu dựng lại được nên để
        # ở Local cho khỏi bơm phồng roaming profile. Game dir noi theo .minecraft,
        # vốn cũng nằm trong Roaming — người chơi quen tìm nó ở đó.
        appdata = _env_dir("APPDATA") or home / "AppData" / "Roaming"
        local = _env_dir("LOCALAPPDATA") or home / "AppData" / "Local"
        return (
            appdata / APP_NAME,
            local / APP_NAME / "Cache",
            appdata / f".{APP_SLUG}",
        )
    if MACOS:
        support = home / "Library" / "Application Support"
        return (
            support / APP_NAME,
            home / "Library" / "Caches" / APP_SLUG,
            support / APP_SLUG,
        )
    # Linux và mọi Unix khác: XDG, có mặc định dự phòng đúng như đặc tả.
    config = _env_dir("XDG_CONFIG_HOME") or home / ".config"
    cache = _env_dir("XDG_CACHE_HOME") or home / ".cache"
    return config / APP_SLUG, cache / APP_SLUG, home / f".{APP_SLUG}"


CONFIG_DIR, CACHE_DIR, DEFAULT_GAME_DIR = _dirs()

# (cũ, mới) — chỉ dời khi bên mới chưa tồn tại, không bao giờ ghi đè.
# Chỉ Linux mới từng chạy bản mang tên mc-launcher, nên Windows/macOS không có gì
# để dời và danh sách bỏ trống.
_LEGACY: list[tuple[Path, Path]] = []
if not WINDOWS and not MACOS:
    _LEGACY = [
        (Path.home() / ".config" / "mc-launcher", CONFIG_DIR),
        (Path.home() / ".cache" / "mc-launcher", CACHE_DIR),
        (Path.home() / ".mc-launcher", DEFAULT_GAME_DIR),
    ]

LEGACY_GAME_DIR = str(Path.home() / ".mc-launcher")


def migrate_legacy() -> list[str]:
    """Dời dữ liệu từ thư mục tên cũ sang tên mới. Trả về danh sách đã dời."""
    moved = []
    for old, new in _LEGACY:
        if old.exists() and not new.exists():
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
            moved.append(f"{old} -> {new}")
    return moved
