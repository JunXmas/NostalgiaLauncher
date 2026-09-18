"""Quét bản chơi của Lunar Client.

Tách khỏi `launchers.py` vì Lunar không có file cấu hình nào khai báo bản game: phải suy từ
cấu trúc thư mục, và phần suy đoán đó dài hơn mọi scanner khác gộp lại.
"""

from __future__ import annotations

import logging
import os
import platform
import re
from pathlib import Path

from nostalgia.importing.model import Found
from nostalgia.modloader.model import LoaderKind, detect_loader_kind

logger = logging.getLogger(__name__)

# Tên thư mục là nguồn DUY NHẤT cho số hiệu bản game. Bắt "1.8.9", "1.21"; không bắt "1"
# trong "Profile74810572142". Chặn hai đầu bằng chữ số/dấu chấm: nếu không, "1.9" bên trong
# "neoforge-21.1.9-1.21.1" khớp trước và cho ra số hiệu loader chứ không phải bản Minecraft.
_VERSION_IN_NAME = re.compile(r"(?<![\d.])(1\.\d+(?:\.\d+)?)(?![\d.])")

# Thư mục con cho thấy đây là game_dir thật chứ không phải một lớp bọc.
_GAME_DIR_MARKERS = ("saves", "mods", "options.txt", "resourcepacks", "config")


def lunar_dirs() -> list[Path]:
    """Các thư mục `.lunarclient` có thể có — bản thường và bản Flatpak trên Linux."""
    sys_plat = platform.system()
    if sys_plat == "Windows":
        # Lunar nằm ở %USERPROFILE%\.lunarclient, KHÔNG phải %APPDATA%.
        return [Path(os.environ.get("USERPROFILE", "~")) / ".lunarclient"]
    if sys_plat not in ("Linux", "Darwin"):
        return []
    candidates = [Path("~/.lunarclient").expanduser()]
    if sys_plat == "Linux":
        candidates.append(Path("~/.var/app/com.lunarclient.Lunarclient/.lunarclient").expanduser())
    return candidates


def _game_dir(inst_dir: Path) -> Path:
    """Thư mục game thật bên trong một bản chơi Lunar.

    Bản chơi cô lập ("Isolated Profiles") giữ saves/mods ngay tại gốc; bản cũ hơn bọc thêm
    một lớp `.minecraft`. Không thấy dấu hiệu nào thì trả chính thư mục gốc.
    """
    for candidate in (inst_dir, inst_dir / ".minecraft"):
        if any((candidate / marker).exists() for marker in _GAME_DIR_MARKERS):
            return candidate
    return inst_dir


def _version_and_loader(inst_dir: Path) -> tuple[str, LoaderKind]:
    """Suy bản game + loader từ thư mục `versions/`, không có thì từ tên bản chơi."""
    versions_dir = inst_dir / "versions"
    if versions_dir.is_dir():
        for version_dir in sorted(versions_dir.iterdir()):
            if not version_dir.is_dir():
                continue
            match = _VERSION_IN_NAME.search(version_dir.name)
            if match:
                return match.group(1), detect_loader_kind(version_dir.name)
    match = _VERSION_IN_NAME.search(inst_dir.name)
    return (match.group(1) if match else ""), "vanilla"


def scan_lunar_client() -> list[Found]:
    """Mỗi thư mục con của `.lunarclient/profiles` là một bản chơi."""
    found: list[Found] = []
    for lunar_dir in lunar_dirs():
        instances = lunar_dir / "profiles"
        if not instances.is_dir():
            continue
        for inst_dir in instances.iterdir():
            if not inst_dir.is_dir():
                continue
            try:
                game_version, loader_kind = _version_and_loader(inst_dir)
                found.append(
                    Found(
                        "Lunar Client",
                        inst_dir.name,
                        _game_dir(inst_dir),
                        game_version,
                        loader_kind,
                    )
                )
            except Exception:
                logger.debug("lỗi khi quét bản chơi Lunar Client %s", inst_dir, exc_info=True)
    return found
