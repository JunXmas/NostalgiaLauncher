"""Cài modpack Modrinth (.mrpack) vào một instance.

.mrpack là một zip chứa `modrinth.index.json` (liệt kê phiên bản Minecraft +
loader + danh sách file mod cần tải) và thư mục `overrides/` (config, script…
chép thẳng vào thư mục game). Cài xong ta biết loader + bản game để dựng instance.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from . import install

# Khoá dependency trong index -> loader nội bộ.
_LOADER_KEYS = [
    ("fabric-loader", "fabric"),
    ("quilt-loader", "quilt"),
    ("neoforge", "neoforge"),
    ("forge", "forge"),
]


def read_index(mrpack_path: Path) -> dict:
    with zipfile.ZipFile(mrpack_path) as z:
        return json.loads(z.read("modrinth.index.json"))


def loader_and_mc(index: dict) -> tuple[str, str]:
    """(loader, phiên_bản_minecraft) từ dependencies của pack."""
    deps = index.get("dependencies", {})
    mc = deps.get("minecraft", "")
    for key, loader in _LOADER_KEYS:
        if key in deps:
            return loader, mc
    return "vanilla", mc


def install_contents(mrpack_path: Path, game_dir: Path, on_status=None) -> dict:
    """Bung overrides và tải toàn bộ file mod của pack vào game_dir. Trả về index."""
    game_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(mrpack_path) as z:
        index = json.loads(z.read("modrinth.index.json"))
        for name in z.namelist():
            # overrides/ và client-overrides/ đều chép vào thư mục game.
            for prefix in ("overrides/", "client-overrides/"):
                if name.startswith(prefix) and not name.endswith("/"):
                    dest = game_dir / name[len(prefix):]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(z.read(name))

    files = index.get("files", [])
    total = len(files)
    for i, f in enumerate(files, 1):
        env = f.get("env", {})
        if env.get("client") == "unsupported":
            continue                        # mod chỉ dành cho server -> bỏ
        downloads = f.get("downloads") or []
        if not downloads:
            continue
        dest = game_dir / f["path"]
        if on_status:
            on_status(f"Downloading pack files… {i}/{total}")
        install.download(downloads[0], dest, f.get("hashes", {}).get("sha1"))
    return index
