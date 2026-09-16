"""Quét instance Minecraft từ PrismLauncher, CurseForge, ModrinthApp, TLauncher, Vanilla."""

from __future__ import annotations

import configparser
import dataclasses
import json
import logging
import os
import platform
from pathlib import Path

from nostalgia.modloader.model import LoaderKind

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class Found:
    """Đại diện cho một instance Minecraft từ một launcher khác."""

    launcher: str
    instance_name: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind


def _platform_dir(linux: str, darwin: str, windows: str) -> Path | None:
    """Trả thư mục theo hệ điều hành, hoặc None nếu không hỗ trợ."""
    sys_plat = platform.system()
    if sys_plat == "Linux":
        return Path(linux).expanduser()
    if sys_plat == "Darwin":
        return Path(darwin).expanduser()
    if sys_plat == "Windows":
        return Path(os.environ.get("APPDATA", "~")) / windows
    return None


def _scan_prism() -> list[Found]:
    """PrismLauncher: đọc instance.cfg + mmc-pack.json."""
    base = _platform_dir(
        "~/.local/share/PrismLauncher/instances",
        "~/Library/Application Support/PrismLauncher/instances",
        "PrismLauncher/instances",
    )
    if base is None or not base.exists():
        return []
    found: list[Found] = []
    for inst_dir in base.iterdir():
        if not inst_dir.is_dir() or not (inst_dir / "instance.cfg").exists():
            continue
        try:
            content = "[DEFAULT]\n" + (inst_dir / "instance.cfg").read_text(encoding="utf-8")
            parser = configparser.ConfigParser()
            parser.read_string(content)
            instance_name = parser.get("DEFAULT", "name", fallback=inst_dir.name)
            game_dir = inst_dir / ".minecraft"
            if not game_dir.exists():
                game_dir = inst_dir / "minecraft" if (inst_dir / "minecraft").exists() else inst_dir
            game_version, loader_kind = "", "vanilla"
            mmc_pack = inst_dir / "mmc-pack.json"
            if mmc_pack.exists():
                pack_body = json.loads(mmc_pack.read_text(encoding="utf-8"))
                for comp in pack_body.get("components", []):
                    uid = comp.get("uid", "")
                    if uid == "net.minecraft":
                        game_version = comp.get("version", "")
                    elif uid == "net.fabricmc.fabric-loader":
                        loader_kind = "fabric"
                    elif uid == "org.quiltmc.quilt-loader":
                        loader_kind = "quilt"
                    elif uid == "net.minecraftforge":
                        loader_kind = "forge"
                    elif uid == "net.neoforged.neoforge":
                        loader_kind = "neoforge"
            found.append(Found("PrismLauncher", instance_name, game_dir, game_version, loader_kind))  # type: ignore[arg-type]
        except Exception:
            logger.debug("lỗi khi quét PrismLauncher instance %s", inst_dir, exc_info=True)
    return found


def _scan_curseforge() -> list[Found]:
    """CurseForge (Overwolf): chỉ macOS + Windows."""
    sys_plat = platform.system()
    if sys_plat == "Darwin":
        base = Path("~/Documents/curseforge/minecraft/Instances").expanduser()
    elif sys_plat == "Windows":
        base = Path(os.environ.get("USERPROFILE", "~")) / "curseforge/minecraft/Instances"
    else:
        return []
    if not base.exists():
        return []
    found: list[Found] = []
    for inst_dir in base.iterdir():
        if not inst_dir.is_dir() or not (inst_dir / "minecraftinstance.json").exists():
            continue
        try:
            body = json.loads((inst_dir / "minecraftinstance.json").read_text(encoding="utf-8"))
            loader_kind: LoaderKind = "vanilla"
            loader_name = (body.get("baseModLoader") or {}).get("name", "").lower()
            if "fabric" in loader_name:
                loader_kind = "fabric"
            elif "quilt" in loader_name:
                loader_kind = "quilt"
            elif "neo" in loader_name:
                loader_kind = "neoforge"
            elif "forge" in loader_name:
                loader_kind = "forge"
            found.append(
                Found(
                    "CurseForge",
                    body.get("name", inst_dir.name),
                    inst_dir,
                    body.get("gameVersion", ""),
                    loader_kind,
                )
            )
        except Exception:
            logger.debug("lỗi khi quét CurseForge instance %s", inst_dir, exc_info=True)
    return found


def _scan_modrinth_app() -> list[Found]:
    """ModrinthApp: đọc profile.json."""
    base = _platform_dir(
        "~/.local/share/ModrinthApp/profiles",
        "~/Library/Application Support/ModrinthApp/profiles",
        "ModrinthApp/profiles",
    )
    if base is None or not base.exists():
        return []
    found: list[Found] = []
    for inst_dir in base.iterdir():
        if not inst_dir.is_dir() or not (inst_dir / "profile.json").exists():
            continue
        try:
            body = json.loads((inst_dir / "profile.json").read_text(encoding="utf-8"))
            found.append(
                Found(
                    "ModrinthApp",
                    body.get("name", inst_dir.name),
                    inst_dir,
                    body.get("game_version", ""),
                    body.get("loader", "vanilla").lower(),  # type: ignore[arg-type]
                )
            )
        except Exception:
            logger.debug("lỗi khi quét ModrinthApp profile %s", inst_dir, exc_info=True)
    return found


def _scan_vanilla() -> list[Found]:
    """Official Minecraft launcher."""
    sys_plat = platform.system()
    if sys_plat == "Linux":
        base = Path("~/.minecraft").expanduser()
    elif sys_plat == "Darwin":
        base = Path("~/Library/Application Support/minecraft").expanduser()
    elif sys_plat == "Windows":
        base = Path(os.environ.get("APPDATA", "~")) / ".minecraft"
    else:
        return []
    if not base.exists() or not (base / "versions").is_dir():
        return []
    game_version = ""
    profiles_json = base / "launcher_profiles.json"
    if profiles_json.exists():
        try:
            body = json.loads(profiles_json.read_text(encoding="utf-8"))
            for saved in body.get("profiles", {}).values():
                last_v = saved.get("lastVersionId")
                if last_v:
                    game_version = last_v
                    break
        except Exception:
            logger.debug("lỗi khi đọc launcher_profiles.json", exc_info=True)
    return [Found("Vanilla", "Vanilla Minecraft", base, game_version, "vanilla")]


def find_all() -> list[Found]:
    """Tìm tất cả instances từ mọi launcher. An toàn: không bao giờ ném lỗi."""
    all_found: list[Found] = []
    for scanner in (_scan_prism, _scan_curseforge, _scan_modrinth_app, _scan_vanilla):
        try:
            all_found.extend(scanner())
        except Exception:
            logger.debug("lỗi khi chạy %s", scanner.__name__, exc_info=True)
    all_found.sort(key=lambda x: (x.launcher, x.instance_name))
    return all_found
