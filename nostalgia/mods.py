"""Quản lý file mod / resource pack trong thư mục game.

Bật/tắt theo quy ước Minecraft: thêm đuôi ".disabled" để game bỏ qua file, bỏ
đuôi để bật lại — không xoá gì nên tắt/bật thoải mái. Tải file thì tái dùng
install.download() (đã kiểm tra hash sha1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import install
from .settings import Settings

DISABLED = ".disabled"

# Đuôi hợp lệ cho từng loại nội dung.
KINDS = {
    "mods": (".jar",),
    "resourcepacks": (".zip",),
}


def folder(settings: Settings, kind: str) -> Path:
    """Thư mục dùng chung cho loại nội dung, tạo sẵn nếu chưa có."""
    path = settings.game_path / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def _display_name(name: str) -> str:
    return name[:-len(DISABLED)] if name.endswith(DISABLED) else name


@dataclass
class Item:
    name: str          # tên hiển thị (đã bỏ .disabled)
    path: Path         # đường dẫn thật trên đĩa
    enabled: bool
    size: int


def list_installed(settings: Settings, kind: str) -> list[Item]:
    """Liệt kê file đã có, gồm cả bản đang tắt, sắp theo tên."""
    exts = KINDS[kind]
    out: list[Item] = []
    for p in folder(settings, kind).iterdir():
        if not p.is_file():
            continue
        display = _display_name(p.name)
        if not display.lower().endswith(exts):
            continue
        out.append(Item(
            name=display,
            path=p,
            enabled=not p.name.endswith(DISABLED),
            size=p.stat().st_size,
        ))
    out.sort(key=lambda it: it.name.lower())
    return out


def set_enabled(path: Path, enabled: bool) -> Path:
    """Đổi tên qua lại giữa bản bật và bản .disabled. Trả về đường dẫn mới."""
    if (not path.name.endswith(DISABLED)) == enabled:
        return path
    target = path.with_name(_display_name(path.name) + ("" if enabled else DISABLED))
    path.replace(target)
    return target


def delete(path: Path) -> None:
    path.unlink(missing_ok=True)


def is_installed(settings: Settings, kind: str, filename: str) -> bool:
    """Đã có file này chưa (kể cả bản đang tắt)?"""
    base = folder(settings, kind)
    return (base / filename).exists() or (base / (filename + DISABLED)).exists()


def install_file(settings: Settings, kind: str, *, url: str, filename: str,
                 sha1: str | None = None) -> Path:
    """Tải một file về thư mục tương ứng và trả về đường dẫn."""
    dest = folder(settings, kind) / filename
    return install.download(url, dest, sha1)
