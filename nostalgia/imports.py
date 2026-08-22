"""Dò & đọc instance từ các launcher Minecraft khác để nhập sang Nostalgia.

Mỗi launcher lưu instance một kiểu; ở đây ta chỉ ĐỌC metadata (tên, bản game,
loader) và trả về thư mục game của nó. Việc chép file + cài loader do Controller
làm (tái dùng pipeline sẵn có). Chỉ đọc, không đụng gì tới dữ liệu gốc.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Found:
    launcher: str      # "Prism" / "MultiMC" / "CurseForge" / "Modrinth" / "Vanilla"
    name: str
    game_dir: Path     # thư mục chứa mods/saves/config của instance
    mc: str            # bản Minecraft, vd "1.20.1" ("" nếu không rõ)
    loader: str        # "" | "fabric" | "forge" | "neoforge" | "quilt"


# mmc-pack.json: uid component -> loader nội bộ.
_MMC_LOADER = {
    "net.fabricmc.fabric-loader": "fabric",
    "org.quiltmc.quilt-loader": "quilt",
    "net.minecraftforge": "forge",
    "net.neoforged": "neoforge",
}


def _home() -> Path:
    return Path(os.path.expanduser("~"))


def _appdata() -> Path | None:
    v = os.environ.get("APPDATA")
    return Path(v) if v else None


def _prism_roots() -> list[Path]:
    h = _home()
    roots = [
        h / ".local/share/PrismLauncher/instances",
        h / ".var/app/org.prismlauncher.PrismLauncher/data/PrismLauncher/instances",
        h / "Library/Application Support/PrismLauncher/instances",
        h / ".local/share/multimc/instances",
        h / ".local/share/MultiMC/instances",
        h / "MultiMC/instances",
    ]
    ad = _appdata()
    if ad:
        roots += [ad / "PrismLauncher/instances"]
    return roots


def _curseforge_roots() -> list[Path]:
    h = _home()
    return [
        h / "Documents/curseforge/minecraft/Instances",
        h / "curseforge/minecraft/Instances",
        h / "Documents/Curseforge/Minecraft/Instances",
    ]


def _modrinth_roots() -> list[Path]:
    h = _home()
    roots = [
        h / ".local/share/ModrinthApp/profiles",
        h / "Library/Application Support/ModrinthApp/profiles",
        h / "Library/Application Support/com.modrinth.theseus/profiles",
    ]
    ad = _appdata()
    if ad:
        roots += [ad / "ModrinthApp/profiles", ad / "com.modrinth.theseus/profiles"]
    return roots


def _vanilla_dirs() -> list[Path]:
    h = _home()
    dirs = [h / ".minecraft", h / "Library/Application Support/minecraft"]
    ad = _appdata()
    if ad:
        dirs += [ad / ".minecraft"]
    return dirs


def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        return None


def _prism_instance(inst_dir: Path) -> Found | None:
    pack = _read_json(inst_dir / "mmc-pack.json")
    if not pack:
        return None
    mc, loader = "", ""
    for comp in pack.get("components", []):
        uid = comp.get("uid", "")
        ver = comp.get("version", "") or comp.get("cachedVersion", "")
        if uid == "net.minecraft":
            mc = ver
        elif uid in _MMC_LOADER:
            loader = _MMC_LOADER[uid]
    # thư mục game: .minecraft (mới) hoặc minecraft (cũ)
    game = next((inst_dir / d for d in (".minecraft", "minecraft") if (inst_dir / d).is_dir()),
                None)
    if game is None:
        return None
    name = inst_dir.name
    cfg = inst_dir / "instance.cfg"
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("name="):
                name = line[5:].strip() or name
                break
    return Found("Prism/MultiMC", name, game, mc, loader)


def _curseforge_instance(inst_dir: Path) -> Found | None:
    meta = _read_json(inst_dir / "minecraftinstance.json")
    if not meta:
        return None
    mc = (meta.get("gameVersion") or "")
    base = meta.get("baseModLoader") or {}
    raw = (base.get("name") or "").lower()          # vd "forge-47.2.0", "fabric-0.15"
    loader = next((l for l in ("neoforge", "forge", "fabric", "quilt") if l in raw), "")
    name = meta.get("name") or inst_dir.name
    return Found("CurseForge", name, inst_dir, mc, loader)


def _modrinth_instance(inst_dir: Path) -> Found | None:
    meta = _read_json(inst_dir / "profile.json")
    mc, loader, name = "", "", inst_dir.name
    if isinstance(meta, dict):
        mc = meta.get("game_version") or (meta.get("metadata") or {}).get("game_version") or ""
        loader = (meta.get("loader") or (meta.get("metadata") or {}).get("loader") or "").lower()
        name = meta.get("name") or (meta.get("metadata") or {}).get("name") or name
    # Có thư mục mods hoặc saves thì mới coi là instance thực
    if not any((inst_dir / d).is_dir() for d in ("mods", "saves")):
        return None
    if loader not in ("fabric", "forge", "neoforge", "quilt"):
        loader = ""
    return Found("Modrinth", name, inst_dir, mc, loader)


def _iter_dirs(root: Path):
    try:
        for child in sorted(root.iterdir()):
            if child.is_dir():
                yield child
    except OSError:
        return


def scan() -> list[Found]:
    """Quét mọi launcher đã biết trên máy, trả danh sách instance nhập được."""
    out: list[Found] = []
    seen: set[Path] = set()

    def add(found: Found | None):
        if found and found.game_dir.is_dir():
            key = found.game_dir.resolve()
            if key not in seen:
                seen.add(key)
                out.append(found)

    for root in _prism_roots():
        if root.is_dir():
            for d in _iter_dirs(root):
                add(_prism_instance(d))
    for root in _curseforge_roots():
        if root.is_dir():
            for d in _iter_dirs(root):
                add(_curseforge_instance(d))
    for root in _modrinth_roots():
        if root.is_dir():
            for d in _iter_dirs(root):
                add(_modrinth_instance(d))
    for game in _vanilla_dirs():
        if game.is_dir() and (game / "saves").is_dir():
            add(Found("Vanilla", "Vanilla .minecraft", game, "", ""))
    return out


# Những thứ KHÔNG chép khi nhập (nặng/vô ích/không thuộc về instance).
IGNORE = {"logs", "crash-reports", "assets", "libraries", "versions", "bin",
          ".fabric", "natives", "webcache", "webcache2", "screenshots"}
