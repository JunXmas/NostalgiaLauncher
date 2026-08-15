"""Tự tải JRE do Mojang cung cấp, để người dùng khỏi phải cài Java thủ công.

Mỗi phiên bản game khai báo `javaVersion.component` (jre-legacy = Java 8,
java-runtime-gamma = 17, java-runtime-delta = 21...). Mojang host sẵn đúng bộ
runtime cho từng OS, nên ta chỉ việc tải về thư mục riêng của launcher.
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .install import download

ALL_RUNTIMES = (
    "https://launchermeta.mojang.com/v1/products/java-runtime/"
    "2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json"
)
TIMEOUT = 30
DEFAULT_COMPONENT = "jre-legacy"  # phiên bản cũ không khai component thì mặc định Java 8


def _os_key() -> str:
    system = platform.system()
    machine = platform.machine()
    if system == "Linux":
        return "linux" if machine in ("x86_64", "AMD64", "aarch64", "arm64") else "linux-i386"
    if system == "Darwin":
        return "mac-os-arm64" if machine in ("arm64", "aarch64") else "mac-os"
    if system == "Windows":
        if machine in ("ARM64", "aarch64"):
            return "windows-arm64"
        return "windows-x64" if machine in ("AMD64", "x86_64") else "windows-x86"
    return "linux"


def component_of(meta: dict) -> str:
    return meta.get("javaVersion", {}).get("component", DEFAULT_COMPONENT)


def runtime_dir(game_dir: Path, component: str) -> Path:
    return game_dir / "runtime" / component / _os_key() / component


def java_binary(game_dir: Path, component: str) -> Path:
    """Đường dẫn tới java trong bộ runtime đã tải.

    Bố cục do Mojang quy định và khác nhau theo hệ điều hành: bản macOS đóng gói
    thành bundle nên java nằm sâu trong `jre.bundle/Contents/Home`, còn bản
    Windows thì có đuôi `.exe`. Dùng `java.exe` chứ không phải `javaw.exe` — cả
    hai đều chạy được game, nhưng `javaw` không có stdout nên vừa mất log game
    vừa làm hỏng bước dò `-version`. Cửa sổ console đen thì đã bị chặn từ chỗ
    khác (xem `launch.run`).
    """
    base = runtime_dir(game_dir, component)
    if platform.system() == "Darwin":
        base = base / "jre.bundle" / "Contents" / "Home"
    return base / "bin" / ("java.exe" if platform.system() == "Windows" else "java")


def is_installed(game_dir: Path, component: str) -> bool:
    return java_binary(game_dir, component).is_file()


def _manifest_url(component: str) -> str | None:
    data = requests.get(ALL_RUNTIMES, timeout=TIMEOUT).json()
    entries = data.get(_os_key(), {}).get(component, [])
    if not entries:
        return None
    return entries[0]["manifest"]["url"]


def install(game_dir: Path, component: str, on_progress=None) -> Path:
    """Tải trọn bộ runtime của một component. Trả về đường dẫn java binary."""
    url = _manifest_url(component)
    if url is None:
        raise RuntimeError(
            f"Mojang has no JRE '{component}' for {_os_key()}. "
            "Install Java manually and set its path in Settings."
        )
    manifest = requests.get(url, timeout=TIMEOUT).json()
    base = runtime_dir(game_dir, component)
    files = manifest["files"]

    # Vòng 1: tạo cây thư mục và thu thập link tượng trưng trước.
    links: list[tuple[Path, str]] = []
    jobs: list[tuple[str, Path, str]] = []
    for rel, info in files.items():
        target = base / rel
        kind = info["type"]
        if kind == "directory":
            target.mkdir(parents=True, exist_ok=True)
        elif kind == "link":
            links.append((target, info["target"]))
        elif kind == "file":
            raw = info["downloads"]["raw"]
            jobs.append((raw["url"], target, raw.get("sha1")))

    total = len(jobs)
    done = 0
    if on_progress:
        on_progress("Downloading Java", 0, total)

    def one(job):
        nonlocal done
        url_, dest, sha = job
        dest.parent.mkdir(parents=True, exist_ok=True)
        download(url_, dest, sha)
        # Giữ cờ thực thi cho bin/java và các script.
        if files[str(dest.relative_to(base))].get("executable"):
            dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        if on_progress:
            done += 1
            on_progress("Downloading Java", done, total)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, jobs))

    # Vòng 2: tạo symlink sau khi đích đã tồn tại.
    #
    # Windows chỉ cho tạo symlink khi bật Developer Mode hoặc chạy quyền quản trị,
    # nên chỗ này phải có đường lui: chép hẳn file ra. Tốn thêm ít đĩa, nhưng thà
    # thế còn hơn để nguyên bộ JRE hỏng vì một cái link không tạo được.
    for link_path, tgt in links:
        link_path.parent.mkdir(parents=True, exist_ok=True)
        if link_path.exists() or link_path.is_symlink():
            link_path.unlink()
        try:
            os.symlink(tgt, link_path)
        except (OSError, NotImplementedError):
            source = (link_path.parent / tgt).resolve()
            if source.is_dir():
                shutil.copytree(source, link_path, dirs_exist_ok=True)
            elif source.exists():
                shutil.copy2(source, link_path)

    binary = java_binary(game_dir, component)
    if binary.exists():
        binary.chmod(binary.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return binary


def ensure(game_dir: Path, meta: dict, on_progress=None) -> Path | None:
    """Bảo đảm có JRE cho phiên bản này; tải nếu thiếu. Trả về java binary hoặc None."""
    component = component_of(meta)
    if is_installed(game_dir, component):
        return java_binary(game_dir, component)
    return install(game_dir, component, on_progress)
