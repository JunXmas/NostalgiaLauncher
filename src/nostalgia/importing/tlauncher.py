"""Quét bản chơi của TLauncher.

Tách khỏi `launchers.py` vì TLauncher không giống ba launcher kia ở một điểm cốt lõi: nó
không đẻ thư mục instance để duyệt. Nó chơi thẳng trong MỘT thư mục game, và thư mục đó
người dùng đổi được — chỗ duy nhất biết nó nằm đâu là file cấu hình riêng của TLauncher,
`~/.tlauncher/tlauncher-2.0.properties`, chứ không phải bất cứ file nào trong `.minecraft`.
"""

from __future__ import annotations

import configparser
import logging
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

# Dấu nhận dạng: TLauncher ghi file này vào thư mục game của nó, cạnh `launcher_profiles.json`
# của bản chính chủ. Bản chính chủ không bao giờ tạo nó.
PROFILES_FILENAME = "TlauncherProfiles.json"


def settings() -> dict[str, str]:
    """Đọc `tlauncher-2.0.properties` — .properties phẳng, không có section header.

    Trả rỗng khi không có file hoặc đọc hỏng: quét launcher là việc phải im lặng chịu thua,
    không được ném lỗi lên giao diện.
    """
    sys_plat = platform.system()
    if sys_plat == "Darwin":
        config_dir = Path("~/Library/Application Support/tlauncher").expanduser()
    elif sys_plat in {"Linux", "Windows"}:
        # Windows cũng `~/.tlauncher`: TLauncher tra `user.home`, không tra `%APPDATA%`.
        config_dir = Path("~/.tlauncher").expanduser()
    else:
        return {}
    settings_file = config_dir / "tlauncher-2.0.properties"
    if not settings_file.is_file():
        return {}
    try:
        # `interpolation=None`: đường dẫn Windows có `%` mà ConfigParser mặc định đòi nội suy.
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string("[DEFAULT]\n" + settings_file.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("lỗi khi đọc tlauncher-2.0.properties", exc_info=True)
        return {}
    return dict(parser["DEFAULT"])


def game_dir(default_minecraft_dir: Path | None) -> Path | None:
    """Thư mục game của TLauncher, hoặc None nếu máy này không có TLauncher.

    `minecraft.gamedir` chỉ có mặt khi người dùng đã đổi thư mục; mặc định thì TLauncher
    dùng chung `.minecraft` với bản chính chủ.
    """
    configured = settings().get("minecraft.gamedir", "").strip()
    base = Path(configured).expanduser() if configured else default_minecraft_dir
    if base is None or not (base / PROFILES_FILENAME).is_file():
        return None
    return base


def selected_version() -> str:
    """Bản game đang chọn trong TLauncher, rỗng nếu không đọc được."""
    return settings().get("login.version.game", "").strip()
