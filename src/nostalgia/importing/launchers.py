"""Quét instance Minecraft từ PrismLauncher, CurseForge, ModrinthApp, TLauncher, Vanilla.

Trên Linux, một launcher cài bằng **Flatpak** KHÔNG ghi vào `~/.local/share`: hộp cát đổi
hướng nó sang `~/.var/app/<id>/data`. Quét mỗi đường quen thuộc là trả về rỗng ngay trên máy
có sẵn ba bản chơi — đúng lỗi Jun gặp 17/09/2026. Vì thế mỗi launcher khai một DANH SÁCH
thư mục gốc, không phải một thư mục.
"""

from __future__ import annotations

import configparser
import dataclasses
import json
import logging
import os
import platform
from pathlib import Path

from nostalgia.importing import tlauncher
from nostalgia.modloader.model import LoaderKind, detect_loader_kind

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class Found:
    """Đại diện cho một instance Minecraft từ một launcher khác."""

    launcher: str
    instance_name: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind


def _platform_dirs(linux: str, darwin: str, windows: str, flatpak: str = "") -> list[Path]:
    """Mọi thư mục cần soi theo hệ điều hành — có thể rỗng nếu hệ này không hỗ trợ.

    Trả DANH SÁCH vì trên Linux cùng một launcher có hai chỗ ở: bản cài thường nằm dưới
    `~/.local/share`, bản Flatpak nằm trong hộp cát `~/.var/app/<id>/data`.
    """
    sys_plat = platform.system()
    if sys_plat == "Linux":
        paths = [Path(linux).expanduser()]
        if flatpak:
            # Flatpak dựng lại đúng cây `~/.local/share` bên trong hộp cát, nên phần đuôi
            # sau `~/.local/share/` giữ nguyên — chỉ đổi phần gốc.
            tail = linux.removeprefix("~/.local/share/")
            paths.append(Path(f"~/.var/app/{flatpak}/data/{tail}").expanduser())
        return paths
    if sys_plat == "Darwin":
        return [Path(darwin).expanduser()]
    if sys_plat == "Windows":
        return [Path(os.environ.get("APPDATA", "~")) / windows]
    return []


def _instance_dirs(bases: list[Path]) -> list[Path]:
    """Mọi thư mục con của mọi thư mục gốc có thật. Thư mục gốc không tồn tại thì bỏ qua."""
    return [
        inst_dir
        for base in bases
        if base.is_dir()
        for inst_dir in sorted(base.iterdir())
        if inst_dir.is_dir()
    ]


def _scan_prism() -> list[Found]:
    """PrismLauncher: đọc instance.cfg + mmc-pack.json. Gồm cả bản cài bằng Flatpak."""
    bases = _platform_dirs(
        "~/.local/share/PrismLauncher/instances",
        "~/Library/Application Support/PrismLauncher/instances",
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
    """ModrinthApp: đọc profile.json. Gồm cả bản cài bằng Flatpak."""
    bases = _platform_dirs(
        "~/.local/share/ModrinthApp/profiles",
        "~/Library/Application Support/ModrinthApp/profiles",
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


def _minecraft_dir() -> Path | None:
    """Thư mục `.minecraft` mặc định của hệ này — nơi ở chung của bản chính chủ và TLauncher."""
    sys_plat = platform.system()
    if sys_plat == "Linux":
        return Path("~/.minecraft").expanduser()
    if sys_plat == "Darwin":
        return Path("~/Library/Application Support/minecraft").expanduser()
    if sys_plat == "Windows":
        return Path(os.environ.get("APPDATA", "~")) / ".minecraft"
    return None


def _last_version_id(base: Path) -> str:
    """Bản game gần nhất ghi trong `launcher_profiles.json`, rỗng nếu đọc không được."""
    profiles_json = base / "launcher_profiles.json"
    if not profiles_json.exists():
        return ""
    try:
        body = json.loads(profiles_json.read_text(encoding="utf-8"))
        for saved in body.get("profiles", {}).values():
            last_v = saved.get("lastVersionId")
            if last_v:
                return str(last_v)
    except Exception:
        logger.debug("lỗi khi đọc launcher_profiles.json", exc_info=True)
    return ""


def _scan_tlauncher() -> list[Found]:
    """TLauncher: thư mục game lấy từ config riêng của nó, chứ không đoán là `.minecraft`.

    TLauncher không đẻ thư mục instance như Prism; nó chơi thẳng trong một thư mục game duy
    nhất, mặc định là `.minecraft` dùng chung với bản chính chủ. Nhưng người dùng đổi được
    thư mục đó trong phần cài đặt, và khi đã đổi thì chỉ `minecraft.gamedir` biết nó ở đâu.
    """
    base = tlauncher.game_dir(_minecraft_dir())
    if base is None:
        return []
    # `login.version.game` là bản đang chọn; `launcher_profiles.json` chỉ là đường lui.
    game_version = tlauncher.selected_version() or _last_version_id(base)
    loader_kind = detect_loader_kind(game_version)
    return [Found("TLauncher", "TLauncher Minecraft", base, game_version, loader_kind)]


def _scan_vanilla() -> list[Found]:
    """Launcher chính chủ.

    Bỏ qua khi `TlauncherProfiles.json` nằm cùng thư mục: lúc đó `.minecraft` là nhà của
    TLauncher và `_scan_tlauncher` đã kể nó rồi — kể lần nữa là một bản chơi hiện hai dòng.
    """
    base = _minecraft_dir()
    if base is None or not base.exists() or not (base / "versions").is_dir():
        return []
    if (base / tlauncher.PROFILES_FILENAME).is_file():
        return []
    return [Found("Vanilla", "Vanilla Minecraft", base, _last_version_id(base), "vanilla")]


def find_all() -> list[Found]:
    """Tìm tất cả instances từ mọi launcher. An toàn: không bao giờ ném lỗi."""
    all_found: list[Found] = []
    for scanner in (
        _scan_prism,
        _scan_curseforge,
        _scan_modrinth_app,
        _scan_tlauncher,
        _scan_vanilla,
    ):
        try:
            all_found.extend(scanner())
        except Exception:
            logger.debug("lỗi khi chạy %s", scanner.__name__, exc_info=True)
    all_found.sort(key=lambda x: (x.launcher, x.instance_name))
    return all_found
