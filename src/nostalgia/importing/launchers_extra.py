"""Quet TLauncher va SKlauncher -- hai launcher khong de instance rieng nhu Prism/CurseForge.

Tach khoi launchers.py vi file do da cham tran 200 dong code cua tests/test_conventions.py.
Module nay tu doc HOME/platform.system() rieng (khong import _home()/_app_bases() tu
launchers.py) du trung vai dong -- launchers.py can goi _scan_tlauncher() va
_scan_sklauncher() o day, nen neu file nay quay lai import launchers.py thi do thi import
co chu trinh (GLOSSARY.md SS5 cam, test_imports_have_no_cycles gac). Found cung dat o day
vi ly do tuong tu: launchers.py import no tu day, khong phai chieu nguoc lai.
"""

from __future__ import annotations

import configparser
import dataclasses
import json
import logging
import os
import platform
from pathlib import Path

from nostalgia.modloader.model import LoaderKind, detect_loader_kind

logger = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True, slots=True)
class Found:
    """Dai dien cho mot instance Minecraft tu mot launcher khac."""

    launcher: str
    instance_name: str
    game_dir: Path
    game_version: str
    loader_kind: LoaderKind


def _home() -> Path:
    """Thu muc nha, doc tu bien moi truong -- khong expanduser() (luat SS1.4)."""
    return Path(os.environ.get("USERPROFILE" if platform.system() == "Windows" else "HOME", "."))


def _default_game_dir() -> Path | None:
    """Thu muc .minecraft mac dinh tren he nay.

    Ban chinh chu, TLauncher (chua doi cau hinh rieng) va SKlauncher 3.2 deu tru chung o day.
    """
    home = _home()
    sys_plat = platform.system()
    if sys_plat == "Linux":
        return home / ".minecraft"
    if sys_plat == "Darwin":
        return home / "Library/Application Support/minecraft"
    if sys_plat == "Windows":
        appdata = os.environ.get("APPDATA")
        return (Path(appdata) if appdata else home / "AppData/Roaming") / ".minecraft"
    return None


TLAUNCHER_MARKER = "TlauncherProfiles.json"


def _tlauncher_config_dir() -> Path | None:
    """~/.tlauncher tren Linux/Windows -- TLauncher tra user.home, khong tra %APPDATA%."""
    sys_plat = platform.system()
    if sys_plat == "Darwin":
        return _home() / "Library/Application Support/tlauncher"
    if sys_plat in {"Linux", "Windows"}:
        return _home() / ".tlauncher"
    return None


def _tlauncher_settings() -> dict[str, str]:
    """Doc tlauncher-2.0.properties -- .properties phang, khong co section header."""
    config_dir = _tlauncher_config_dir()
    if config_dir is None:
        return {}
    settings_file = config_dir / "tlauncher-2.0.properties"
    if not settings_file.is_file():
        return {}
    try:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string("[DEFAULT]\n" + settings_file.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("loi khi doc tlauncher-2.0.properties", exc_info=True)
        return {}
    return dict(parser["DEFAULT"])


def _scan_tlauncher() -> list[Found]:
    """TLauncher: thu muc game tu config rieng, chu khong doan .minecraft.

    Mac dinh TLauncher choi chung .minecraft voi ban chinh chu, nhung doi duoc trong phan
    cai dat -- chi minecraft.gamedir trong config rieng biet no o dau sau khi doi.
    """
    settings = _tlauncher_settings()
    configured = settings.get("minecraft.gamedir", "").strip()
    game_dir = Path(configured) if configured else _default_game_dir()
    if game_dir is None or not (game_dir / TLAUNCHER_MARKER).is_file():
        return []
    game_version = settings.get("login.version.game", "").strip()
    loader_kind = detect_loader_kind(game_version)
    return [Found("TLauncher", "TLauncher Minecraft", game_dir, game_version, loader_kind)]


SKLAUNCHER_MARKER_DIRNAME = "sklauncher"


def _sklauncher_bases() -> list[Path]:
    """Moi cho SKlauncher 3.2 co the de launcher_profiles.json, theo thu tu uu tien."""
    bases: list[Path] = []
    shared = _default_game_dir()
    if shared is not None and (shared / SKLAUNCHER_MARKER_DIRNAME).is_dir():
        bases.append(shared)
    if platform.system() == "Windows":
        appdata = os.environ.get("APPDATA")
        standalone = (Path(appdata) if appdata else _home() / "AppData/Roaming") / "sklauncher"
        if standalone not in bases:
            bases.append(standalone)
    return bases


def _sklauncher_game_version(version_id: str, loader_kind: LoaderKind) -> str:
    """Tach ban game khoi ma ban cua loader: fabric-loader-0.15.0-1.20.1 -> 1.20.1.

    Rong khi ma ban khong noi ra ban game (latest-release, neoforge-21.1.249) -- SKlauncher
    dung chung launcher_profiles.json voi ban chinh chu, va cac ma dang con tro do khong
    phai mot ban choi that; dung instance theo no se tro vao hu khong.
    """
    if loader_kind in {"fabric", "quilt"}:
        return version_id.rsplit("-", 1)[-1]
    if loader_kind in {"forge", "neoforge"}:
        head = version_id.split("-", 1)[0]
        return "" if head.lower() in {"forge", "neoforge"} else head
    return "" if version_id.startswith("latest-") else version_id


def _load_sklauncher_profiles(base: Path) -> list[Found]:
    """Doc tung ban cai trong launcher_profiles.json cua mot thu muc SKlauncher."""
    profiles_json = base / "launcher_profiles.json"
    if not profiles_json.exists():
        return []
    found: list[Found] = []
    try:
        body = json.loads(profiles_json.read_text(encoding="utf-8"))
        profiles = body.get("profiles")
        for key, saved in (profiles if isinstance(profiles, dict) else {}).items():
            if not isinstance(saved, dict):
                continue
            version_id = saved.get("lastVersionId") or ""
            loader_kind = detect_loader_kind(version_id)
            game_version = _sklauncher_game_version(version_id, loader_kind)
            if not game_version:
                logger.debug("bo qua profile SKlauncher %s: khong ro ban game", key)
                continue
            game_dir = Path(saved["gameDir"]) if saved.get("gameDir") else base
            instance_name = saved.get("name") or key
            found.append(Found("SKlauncher", instance_name, game_dir, game_version, loader_kind))
    except Exception:
        logger.debug("loi khi doc launcher_profiles.json cua SKlauncher %s", base, exc_info=True)
    return found


def _scan_sklauncher() -> list[Found]:
    """SKlauncher: moi thu muc co dau sklauncher/, cong ban Setup rieng tren Windows."""
    found: list[Found] = []
    for base in _sklauncher_bases():
        found.extend(_load_sklauncher_profiles(base))
    return found
