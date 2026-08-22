"""Cài modpack Modrinth (.mrpack) vào một instance.

.mrpack là một zip chứa `modrinth.index.json` (liệt kê phiên bản Minecraft +
loader + danh sách file mod cần tải) và thư mục `overrides/` (config, script…
chép thẳng vào thư mục game). Cài xong ta biết loader + bản game để dựng instance.
"""

from __future__ import annotations

import json
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor
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


def is_mrpack(path: Path) -> bool:
    """File này có phải .mrpack (zip chứa modrinth.index.json) không?"""
    try:
        with zipfile.ZipFile(path) as z:
            return "modrinth.index.json" in z.namelist()
    except (OSError, zipfile.BadZipFile):
        return False


def loader_and_mc(index: dict) -> tuple[str, str]:
    """(loader, phiên_bản_minecraft) từ dependencies của pack."""
    deps = index.get("dependencies", {})
    mc = deps.get("minecraft", "")
    for key, loader in _LOADER_KEYS:
        if key in deps:
            return loader, mc
    return "vanilla", mc


def install_contents(mrpack_path: Path, game_dir: Path,
                     on_status=None, on_progress=None) -> dict:
    """Bung overrides và tải toàn bộ file mod của pack (song song) vào game_dir."""
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

    jobs = []
    for f in index.get("files", []):
        if f.get("env", {}).get("client") == "unsupported":
            continue                        # mod chỉ dành cho server -> bỏ
        dl = f.get("downloads") or []
        if dl:
            jobs.append((dl[0], game_dir / f["path"], f.get("hashes", {}).get("sha1")))

    total = len(jobs)
    if on_status:
        on_status(f"Downloading {total} pack files…")
    if on_progress:
        on_progress(0, total)
    done = [0]
    lock = threading.Lock()

    def one(job):
        url, dest, sha = job
        install.download(url, dest, sha)
        with lock:
            done[0] += 1
            if on_progress:
                on_progress(done[0], total)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, jobs))
    return index
