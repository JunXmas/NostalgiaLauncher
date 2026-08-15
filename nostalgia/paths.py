"""Tên chương trình và các thư mục dữ liệu, kèm chuyển đổi từ tên cũ.

Dự án từng mang tên `mc-launcher`. Đổi tên mà bỏ mặc dữ liệu cũ thì người dùng
mất tài khoản đã đăng nhập và cấu hình, nên chỗ này lo việc dời sang tên mới.
"""

from __future__ import annotations

from pathlib import Path

APP_NAME = "Nostalgia Launcher"
APP_SLUG = "nostalgia-launcher"
APP_VERSION = "0.2"

CONFIG_DIR = Path.home() / ".config" / APP_SLUG
CACHE_DIR = Path.home() / ".cache" / APP_SLUG
DEFAULT_GAME_DIR = Path.home() / f".{APP_SLUG}"

# (cũ, mới) — chỉ dời khi bên mới chưa tồn tại, không bao giờ ghi đè.
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
