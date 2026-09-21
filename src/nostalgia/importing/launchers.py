"""Quét instance Minecraft từ PrismLauncher, CurseForge, ModrinthApp, Vanilla."""

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
    """Thư mục nhà, đọc từ biến môi trường.

    Không dùng `expanduser()`: luật §1.4 của kho cấm, vì nó tra thẳng hệ điều hành và test
    không chặn được — đúng cái đã làm mất dữ liệu một lần.
    """
    return Path(os.environ.get("USERPROFILE" if platform.system() == "Windows" else "HOME", "."))


def _app_bases(linux_subdir: str, flatpak_app_id: str, darwin_dir: str) -> list[Path]:
    """Mọi chỗ trên mỗi hệ điều hành launcher này có thể để dữ liệu, theo thứ tự ưu tiên.

    Bản Flatpak trên Linux ghi vào `~/.var/app/<app-id>/data`, không phải `~/.local/share`
    — đây là cách cài phổ biến nhất, bỏ qua nó thì danh sách luôn rỗng. `linux_subdir` cũng
    dùng lại cho Windows (`%APPDATA%/<linux_subdir>`) vì hai launcher trong module này đặt
    tên thư mục con giống nhau trên hai hệ đó.
    """
    home = _home()
    sys_plat = platform.system()
    if sys_plat == "Linux":
        xdg_data = (
            Path(os.environ["XDG_DATA_HOME"])
            if os.environ.get("XDG_DATA_HOME")
            else home / ".local/share"
        )
        return [
            xdg_data / linux_subdir,
            home / ".var/app" / flatpak_app_id / "data" / linux_subdir,
            home / ".local/share" / linux_subdir,
        ]
    if sys_plat == "Darwin":
        return [home / darwin_dir]
    if sys_plat == "Windows":
        appdata = os.environ.get("APPDATA")
        return [(Path(appdata) if appdata else home / "AppData/Roaming") / linux_subdir]
    return []


def _prism_bases() -> list[Path]:
    """Mọi chỗ PrismLauncher có thể để thư mục instances, theo thứ tự ưu tiên."""
    return _app_bases(
        "PrismLauncher/instances",
        "org.prismlauncher.PrismLauncher",
        "Library/Application Support/PrismLauncher/instances",
    )


def _prism_instance_name(cfg: Path, fallback: str) -> str:
    """Đọc `name=` trong instance.cfg.

    File này là INI có section `[General]`, nhưng bản cũ lại không có section nào. Đọc thô
    (không nội suy `%`) vì mục `[UI]` chứa base64 làm ConfigParser thường ném lỗi.
    """
    parser = configparser.RawConfigParser()
    parser.read_string("[__nostalgia__]\n" + cfg.read_text(encoding="utf-8"))
    for section in ("General", "__nostalgia__"):
        name = parser.get(section, "name", fallback="").strip()
        if name:
            return name
    return fallback


def _scan_prism() -> list[Found]:
    """PrismLauncher: đọc instance.cfg + mmc-pack.json."""
    found: list[Found] = []
    seen: set[Path] = set()
    for base in _prism_bases():
        if not base.is_dir() or base.resolve() in seen:
            continue
        seen.add(base.resolve())
        for inst_dir in base.iterdir():
            if not inst_dir.is_dir() or not (inst_dir / "instance.cfg").exists():
                continue
            try:
                instance_name = _prism_instance_name(inst_dir / "instance.cfg", inst_dir.name)
                game_dir = inst_dir / ".minecraft"
                if not game_dir.exists():
                    game_dir = (
                        inst_dir / "minecraft" if (inst_dir / "minecraft").exists() else inst_dir
                    )
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
                found.append(
                    Found("PrismLauncher", instance_name, game_dir, game_version, loader_kind)
                )
            except Exception:
                logger.debug("lỗi khi quét PrismLauncher instance %s", inst_dir, exc_info=True)
    return found


def _scan_curseforge() -> list[Found]:
    """CurseForge (Overwolf): chỉ macOS + Windows."""
    sys_plat = platform.system()
    if sys_plat == "Darwin":
        base = _home() / "Documents/curseforge/minecraft/Instances"
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


def _modrinth_bases() -> list[Path]:
    """Mọi chỗ ModrinthApp có thể để thư mục profiles, theo thứ tự ưu tiên.

    App-id Flatpak `com.modrinth.ModrinthApp` (xem Flathub) — cùng bệnh đã vá cho
    PrismLauncher ở `_prism_bases()`.
    """
    return _app_bases(
        "ModrinthApp/profiles",
        "com.modrinth.ModrinthApp",
        "Library/Application Support/ModrinthApp/profiles",
    )


def _scan_modrinth_app() -> list[Found]:
    """ModrinthApp: đọc profile.json."""
    found: list[Found] = []
    seen: set[Path] = set()
    for base in _modrinth_bases():
        if not base.is_dir() or base.resolve() in seen:
            continue
        seen.add(base.resolve())
        for inst_dir in base.iterdir():
            if not inst_dir.is_dir() or not (inst_dir / "profile.json").exists():
                continue
            try:
                body = json.loads((inst_dir / "profile.json").read_text(encoding="utf-8"))
                raw_loader = body.get("loader", "vanilla").lower()
                _valid_loaders = {"fabric", "quilt", "forge", "neoforge"}
                loader_kind_m: LoaderKind = (
                    raw_loader if raw_loader in _valid_loaders else "vanilla"
                )
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
        base = Path(os.environ.get("APPDATA", "~")) / ".minecraft"
    else:
        return []
    if not base.exists() or not (base / "versions").is_dir():
        return []
    game_version = ""
    profiles_json = base / "launcher_profiles.json"
    if profiles_json.exists():
        try:
            profiles = json.loads(profiles_json.read_text(encoding="utf-8")).get("profiles", {})
            # lastUsed mới nhất thắng; không có lastUsed thì để game_version rỗng, đừng lấy bừa.
            usable = [p for p in profiles.values() if p.get("lastUsed") and p.get("lastVersionId")]
            if usable:
                game_version = max(usable, key=lambda p: p["lastUsed"])["lastVersionId"]
        except Exception:
            # Cả launcher_profiles.json không đọc nổi -> mất hẳn game_version của Vanilla.
            logger.warning("lỗi khi đọc launcher_profiles.json", exc_info=True)
    return [Found("Vanilla", "Vanilla Minecraft", base, game_version, "vanilla")]


def find_all() -> list[Found]:
    """Tìm tất cả instances từ mọi launcher. An toàn: không bao giờ ném lỗi."""
    all_found: list[Found] = []
    for scanner in (_scan_prism, _scan_curseforge, _scan_modrinth_app, _scan_vanilla):
        try:
            all_found.extend(scanner())
        except Exception:
            # Cả một bộ quét chết -> nguyên launcher biến mất khỏi danh sách, người dùng
            # không hiểu vì sao.
            logger.warning("lỗi khi chạy %s", scanner.__name__, exc_info=True)
    all_found.sort(key=lambda x: (x.launcher, x.instance_name))
    return all_found
