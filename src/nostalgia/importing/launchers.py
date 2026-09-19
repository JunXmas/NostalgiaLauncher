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


def _home() -> Path:
    """Thư mục home của người dùng, lấy từ biến môi trường.

    Không dùng `Path.home()` / `expanduser()`: GLOSSARY.md §1.4 cấm, và lưới trong
    `tests/conftest.py` chặn thẳng — scanner gọi tới sẽ nổ rồi im lặng trả rỗng, đúng cái bẫy
    đã giấu lỗi Flatpak này. Quét launcher khác là chỗ hiếm hoi buộc phải nhìn ra ngoài
    `DataPaths`, nên đọc biến môi trường một chỗ duy nhất tại đây.
    """
    return Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "/nonexistent")


def _platform_dirs(share: str, darwin: str, windows: str, *, flatpak: str = "") -> list[Path]:
    """Mọi thư mục có thể chứa instance, theo hệ điều hành.

    Trả về danh sách chứ không một đường dẫn: trên Linux cùng một launcher cài bằng gói hệ
    thống thì nằm ở `~/.local/share/<share>`, cài bằng Flatpak lại nằm trong hộp cát
    `~/.var/app/<app-id>/data/<share>`. Trước đây chỉ dò chỗ đầu, nên bỏ sót sạch instance
    của người dùng cài Flatpak — cách cài phổ biến nhất của PrismLauncher trên Linux.
    """
    sys_plat = platform.system()
    if sys_plat == "Linux":
        dirs = [_home() / ".local/share" / share]
        if flatpak:
            dirs.append(_home() / ".var/app" / flatpak / "data" / share)
        return dirs
    if sys_plat == "Darwin":
        return [_home() / darwin]
    if sys_plat == "Windows":
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / windows] if appdata else []
    return []


def _instance_dirs(bases: list[Path]) -> list[Path]:
    """Mọi thư mục con của các thư mục gốc có thật. Gốc không tồn tại thì bỏ qua."""
    return [child for base in bases if base.is_dir() for child in base.iterdir() if child.is_dir()]


def _scan_prism() -> list[Found]:
    """PrismLauncher: đọc instance.cfg + mmc-pack.json."""
    bases = _platform_dirs(
        "PrismLauncher/instances",
        "Library/Application Support/PrismLauncher/instances",
        "PrismLauncher/instances",
        flatpak="org.prismlauncher.PrismLauncher",
    )
    found: list[Found] = []
    for inst_dir in _instance_dirs(bases):
        if not (inst_dir / "instance.cfg").exists():
            continue
        try:
            content = "[DEFAULT]\n" + (inst_dir / "instance.cfg").read_text(encoding="utf-8")
            parser = configparser.ConfigParser()
            parser.read_string(content)
            instance_name = parser.get("DEFAULT", "name", fallback=inst_dir.name)
            game_dir = inst_dir / ".minecraft"
            if not game_dir.exists():
                game_dir = inst_dir / "minecraft" if (inst_dir / "minecraft").exists() else inst_dir
            game_version: str = ""
            loader_kind: LoaderKind = "vanilla"
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
            found.append(Found("PrismLauncher", instance_name, game_dir, game_version, loader_kind))
        except Exception:
            logger.debug("lỗi khi quét PrismLauncher instance %s", inst_dir, exc_info=True)
    return found


def _scan_curseforge() -> list[Found]:
    """CurseForge (Overwolf): chỉ macOS + Windows."""
    sys_plat = platform.system()
    if sys_plat == "Darwin":
        base = _home() / "Documents/curseforge/minecraft/Instances"
    elif sys_plat == "Windows":
        base = _home() / "curseforge/minecraft/Instances"
    else:
        return []
    if not base.is_dir():
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
    bases = _platform_dirs(
        "ModrinthApp/profiles",
        "Library/Application Support/ModrinthApp/profiles",
        "ModrinthApp/profiles",
        flatpak="com.modrinth.ModrinthApp",
    )
    found: list[Found] = []
    for inst_dir in _instance_dirs(bases):
        if not (inst_dir / "profile.json").exists():
            continue
        try:
            body = json.loads((inst_dir / "profile.json").read_text(encoding="utf-8"))
            raw_loader = body.get("loader", "vanilla").lower()
            _valid_loaders = {"fabric", "quilt", "forge", "neoforge"}
            loader_kind_m: LoaderKind = raw_loader if raw_loader in _valid_loaders else "vanilla"
            found.append(
                Found(
                    "ModrinthApp",
                    body.get("name", inst_dir.name),
                    inst_dir,
                    body.get("game_version", ""),
                    loader_kind_m,
                )
            )
        except Exception:
            logger.debug("lỗi khi quét ModrinthApp profile %s", inst_dir, exc_info=True)
    return found


def _scan_vanilla() -> list[Found]:
    """Official Minecraft launcher."""
    sys_plat = platform.system()
    if sys_plat == "Linux":
        base = _home() / ".minecraft"
    elif sys_plat == "Darwin":
        base = _home() / "Library/Application Support/minecraft"
    elif sys_plat == "Windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return []
        base = Path(appdata) / ".minecraft"
    else:
        return []
    if not (base / "versions").is_dir():
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
            # `warning` chứ không `debug`: mức debug đã giấu trọn lỗi Flatpak — scanner nổ,
            # hộp thoại báo "không tìm thấy launcher nào", không một dòng log nào nhìn thấy.
            logger.warning("lỗi khi chạy %s", scanner.__name__, exc_info=True)
    all_found.sort(key=lambda x: (x.launcher, x.instance_name))
    return all_found
