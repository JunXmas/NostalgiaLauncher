"""Quản lý file mod / resource pack trong thư mục game.

Bật/tắt theo quy ước Minecraft: thêm đuôi ".disabled" để game bỏ qua file, bỏ
đuôi để bật lại — không xoá gì nên tắt/bật thoải mái. Tải file thì tái dùng
install.download() (đã kiểm tra hash sha1).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import install

DISABLED = ".disabled"

# Đuôi hợp lệ cho từng loại nội dung.
KINDS = {
    "mods": (".jar",),
    "resourcepacks": (".zip",),
}


def folder(game_dir: Path, kind: str) -> Path:
    """Thư mục mods/resourcepacks của một instance (game_dir), tạo sẵn nếu thiếu."""
    path = game_dir / kind
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


def list_installed(game_dir: Path, kind: str) -> list[Item]:
    """Liệt kê file đã có, gồm cả bản đang tắt, sắp theo tên."""
    exts = KINDS[kind]
    out: list[Item] = []
    for p in folder(game_dir, kind).iterdir():
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


def is_installed(game_dir: Path, kind: str, filename: str) -> bool:
    """Đã có file này chưa (kể cả bản đang tắt)?"""
    base = folder(game_dir, kind)
    return (base / filename).exists() or (base / (filename + DISABLED)).exists()


def install_file(game_dir: Path, kind: str, *, url: str, filename: str,
                 sha1: str | None = None) -> Path:
    """Tải một file về thư mục tương ứng và trả về đường dẫn."""
    dest = folder(game_dir, kind) / filename
    return install.download(url, dest, sha1)


def file_sha1(path: Path) -> str:
    return install._sha1(path)


def update_item(game_dir: Path, kind: str, item: "Item", new_file: dict) -> Path:
    """Cập nhật một mod: tải bản mới, giữ nguyên trạng thái bật/tắt, bỏ file cũ."""
    base = folder(game_dir, kind)
    new_path = install.download(new_file["url"], base / new_file["filename"],
                                new_file.get("sha1"))
    if not item.enabled:
        new_path = set_enabled(new_path, False)   # bản cũ đang tắt -> giữ tắt
    if item.path != new_path and item.path.exists():
        delete(item.path)                          # xoá file cũ (tên khác)
    return new_path
