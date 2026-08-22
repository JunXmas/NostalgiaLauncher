"""Quản lý file mod / resource pack trong thư mục game.

Bật/tắt theo quy ước Minecraft: thêm đuôi ".disabled" để game bỏ qua file, bỏ
đuôi để bật lại — không xoá gì nên tắt/bật thoải mái. Tải file thì tái dùng
install.download() (đã kiểm tra hash sha1).
"""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import install

DISABLED = ".disabled"


def content_icon(path: Path) -> bytes | None:
    """Rút icon của một mod / resource pack / shader từ file .jar/.zip.

    Đọc khai báo icon theo từng định dạng (Fabric/Quilt/Forge/NeoForge/mcmod), rồi
    lùi về các đường dẫn icon thông dụng (pack.png, icon.png…). Trả về PNG/ảnh bytes
    hoặc None nếu không có.
    """
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            want: list[str] = []

            def js(name):
                try:
                    return json.loads(z.read(name).decode("utf-8", "replace"))
                except (KeyError, ValueError):
                    return None

            if "fabric.mod.json" in names:
                d = js("fabric.mod.json") or {}
                ic = d.get("icon")
                if isinstance(ic, str):
                    want.append(ic)
                elif isinstance(ic, dict) and ic:   # {"64":"...","128":"..."} -> lấy lớn nhất
                    big = sorted(ic, key=lambda k: int(k) if k.isdigit() else 0)[-1]
                    want.append(ic[big])
            if "quilt.mod.json" in names:
                d = js("quilt.mod.json") or {}
                ic = (d.get("quilt_loader", {}).get("metadata", {}) or {}).get("icon")
                if isinstance(ic, str):
                    want.append(ic)
            for toml_name in ("META-INF/mods.toml", "META-INF/neoforge.mods.toml"):
                if toml_name in names:
                    try:
                        txt = z.read(toml_name).decode("utf-8", "replace")
                        m = re.search(r'logoFile\s*=\s*"([^"]+)"', txt)
                        if m:
                            want.append(m.group(1))
                    except KeyError:
                        pass
            if "mcmod.info" in names:                # Forge 1.12-
                arr = js("mcmod.info")
                if isinstance(arr, list):
                    want += [e["logoFile"] for e in arr
                             if isinstance(e, dict) and e.get("logoFile")]

            want += ["icon.png", "pack.png", "logo.png", "logoFile.png"]
            for c in want:
                c = c.lstrip("/")
                if c in names:
                    data = z.read(c)
                    if data:
                        return data
            for n in names:                          # bí quá: assets/<mod>/icon.png
                if n.startswith("assets/") and n.endswith("/icon.png"):
                    return z.read(n)
    except (OSError, zipfile.BadZipFile):
        return None
    return None

# Đuôi hợp lệ cho từng loại nội dung.
KINDS = {
    "mods": (".jar",),
    "resourcepacks": (".zip",),
    "shaderpacks": (".zip",),
}


def folder(game_dir: Path, kind: str) -> Path:
    """Thư mục mods/resourcepacks của một instance (game_dir), tạo sẵn nếu thiếu."""
    path = game_dir / kind
    path.mkdir(parents=True, exist_ok=True)
    return path


def import_local(game_dir: Path, kind: str, src) -> Path:
    """Chép một file mod/resourcepack/shader từ máy vào đúng thư mục của instance.

    Chỉ nhận đúng phần mở rộng của loại (mods=.jar, resourcepacks/shaderpacks=.zip);
    file lạ -> ValueError. Không đè: nếu trùng tên thì thêm hậu tố ' (1)', ' (2)'…
    """
    src = Path(src)
    exts = KINDS.get(kind, ())
    if not src.name.lower().endswith(exts):
        raise ValueError(f"{src.name} is not a {'/'.join(exts)} file.")
    dst_dir = folder(game_dir, kind)
    dest = dst_dir / src.name
    if dest.exists():
        stem, suffix = src.stem, src.suffix
        i = 1
        while (dst_dir / f"{stem} ({i}){suffix}").exists():
            i += 1
        dest = dst_dir / f"{stem} ({i}){suffix}"
    shutil.copy2(src, dest)
    return dest


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
