"""Cài mod loader cho một phiên bản: Vanilla / Fabric / Forge / NeoForge.

Vanilla và Fabric chạy trọn vẹn. Forge/NeoForge cài bằng cách chạy chính
"installer jar" chính thức của họ (chế độ --installClient, không cần GUI): nó
tự sinh version JSON kiểu inheritsFrom + tải thư viện, giống hệt Fabric, nên
launch dùng lại đúng bộ máy sẵn có.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import requests

from . import fabric

TIMEOUT = 30

FORGE_PROMOS = "https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json"
FORGE_INSTALLER = ("https://maven.minecraftforge.net/net/minecraftforge/forge/"
                   "{mc}-{ver}/forge-{mc}-{ver}-installer.jar")
NEOFORGE_META = "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml"
NEOFORGE_INSTALLER = ("https://maven.neoforged.net/releases/net/neoforged/neoforge/"
                      "{ver}/neoforge-{ver}-installer.jar")

# Loader hiển thị trên UI -> khoá nội bộ.
UI_LOADERS = [("Vanilla", "vanilla"), ("Fabric", "fabric"),
              ("Forge", "forge"), ("NeoForge", "neoforge")]


def game_versions(loader: str) -> list[str] | None:
    """Danh sách bản Minecraft mà loader hỗ trợ. None = dùng danh sách vanilla."""
    if loader == "fabric":
        return fabric.list_game_versions()
    if loader == "forge":
        promos = requests.get(FORGE_PROMOS, timeout=TIMEOUT).json().get("promos", {})
        seen, out = set(), []
        for key in promos:                      # key: "1.20.1-recommended"
            mc = key.rsplit("-", 1)[0]
            if mc not in seen:
                seen.add(mc)
                out.append(mc)
        return out
    if loader == "neoforge":
        return _neoforge_game_versions()
    return None                                  # vanilla -> caller dùng list Mojang


def _forge_version(mc: str) -> str:
    promos = requests.get(FORGE_PROMOS, timeout=TIMEOUT).json().get("promos", {})
    return promos.get(f"{mc}-recommended") or promos.get(f"{mc}-latest") or ""


def _neoforge_all(mc: str | None = None) -> list[str]:
    import re
    xml = requests.get(NEOFORGE_META, timeout=TIMEOUT).text
    versions = re.findall(r"<version>([^<]+)</version>", xml)
    if mc:
        # mc "1.20.4" -> neoforge bắt đầu "20.4."; "1.21" -> "21.0."
        parts = mc.split(".")
        major = parts[1] if len(parts) > 1 else ""
        minor = parts[2] if len(parts) > 2 else "0"
        prefix = f"{major}.{minor}."
        versions = [v for v in versions if v.startswith(prefix)]
    return versions


def _neoforge_game_versions() -> list[str]:
    seen, out = set(), []
    for v in _neoforge_all():                    # "20.4.190" -> "1.20.4"
        parts = v.split(".")
        if len(parts) >= 2:
            mc = f"1.{parts[0]}" if parts[1] == "0" else f"1.{parts[0]}.{parts[1]}"
            if mc not in seen:
                seen.add(mc)
                out.append(mc)
    return out


def _run_installer(url: str, installer, java_binary: str, on_status=None) -> str:
    """Tải installer jar và chạy --installClient, trả về id version mới sinh ra."""
    store = installer.store_root
    store.mkdir(parents=True, exist_ok=True)
    # Installer đòi có launcher_profiles.json kiểu launcher Mojang.
    profiles = store / "launcher_profiles.json"
    if not profiles.exists():
        profiles.write_text(json.dumps({"profiles": {}, "settings": {}, "version": 3}))

    jar = store / "installer-tmp.jar"
    from .install import download
    if on_status:
        on_status("Downloading loader installer…")
    download(url, jar)

    before = {p.name for p in installer.versions_dir.glob("*") if p.is_dir()} \
        if installer.versions_dir.exists() else set()

    # Installer đời cũ (vd Forge 1.12.2) tải hàng chục thư viện; chỉ cần một cú
    # rớt kết nối là nó bỏ cuộc ("These libraries failed to download. Try again.").
    # Chạy lại vài lần — lần sau installer bỏ qua lib đã validate nên hội tụ nhanh.
    attempts = 3
    last = ""
    for attempt in range(attempts):
        if on_status:
            on_status("Running loader installer — this can take a few minutes…"
                      + (f" (retry {attempt})" if attempt else ""))
        try:
            proc = subprocess.run(
                [java_binary, "-jar", str(jar), "--installClient", str(store)],
                capture_output=True, text=True, timeout=600)   # đừng treo vĩnh viễn
        except subprocess.TimeoutExpired:
            last = "Installer timed out (>10 min) — network too slow or it hung."
            continue
        after = {p.name for p in installer.versions_dir.glob("*") if p.is_dir()}
        new = sorted(after - before)
        # Thành công theo dòng chốt của installer (đáng tin hơn returncode ở các bản
        # Forge đời cũ). Ưu tiên dir mới xuất hiện; nếu không (vd cài lại), dò dir
        # forge khớp phiên bản này.
        ok = "Successfully installed" in proc.stdout or (proc.returncode == 0 and new)
        if ok:
            vid = new[-1] if new else _loader_dir(after)
            if vid:
                jar.unlink(missing_ok=True)
                return vid
        last = f"{proc.stdout[-500:]}\n{proc.stderr[-300:]}"
        if attempt < attempts - 1:
            time.sleep(2.0 * (attempt + 1))

    jar.unlink(missing_ok=True)
    raise RuntimeError(f"Loader installer failed after {attempts} tries:\n{last}")


def _loader_dir(dirs: set[str]) -> str:
    """Chọn thư mục version do Forge/NeoForge sinh ra (khi cài lại, dir đã tồn tại
    từ trước nên không nằm trong tập 'mới')."""
    cands = [d for d in dirs if "forge" in d.lower()]
    return sorted(cands)[-1] if cands else ""


def install(installer, loader: str, game_version: str,
            java_binary: str | None = None, on_status=None) -> str:
    """Cài loader cho game_version, trả về id phiên bản để chạy."""
    if loader in ("", "vanilla"):
        return game_version
    if loader == "fabric":
        return fabric.install(installer, game_version)
    if loader == "forge":
        ver = _forge_version(game_version)
        if not ver:
            raise RuntimeError(f"No Forge build for {game_version}.")
        if not java_binary:
            raise RuntimeError("Forge needs Java to install (none provided).")
        return _run_installer(FORGE_INSTALLER.format(mc=game_version, ver=ver),
                              installer, java_binary, on_status)
    if loader == "neoforge":
        matches = _neoforge_all(game_version)
        if not matches:
            raise RuntimeError(f"No NeoForge build for {game_version}.")
        if not java_binary:
            raise RuntimeError("NeoForge needs Java to install (none provided).")
        return _run_installer(NEOFORGE_INSTALLER.format(ver=matches[-1]),
                              installer, java_binary, on_status)
    raise RuntimeError(f"Unknown loader: {loader}")
