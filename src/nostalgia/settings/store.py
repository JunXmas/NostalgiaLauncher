"""Đọc/ghi `settings.json` trong `config_dir`."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from nostalgia.errors import DataFileError
from nostalgia.model.json_value import as_integer, as_mapping, as_string
from nostalgia.repo.endpoints import DISCORD_APPLICATION_ID
from nostalgia.storage.files import atomic_write_json, read_json

SETTINGS_FILE_NAME = "settings.json"
# Biến môi trường đè lên file: tiện cho CI và cho người không muốn lưu khoá xuống đĩa.
CURSEFORGE_KEY_ENV = "NOSTALGIA_CURSEFORGE_API_KEY"
DISCORD_APP_ID_ENV = "NOSTALGIA_DISCORD_APP_ID"


@dataclass(frozen=True, slots=True)
class Settings:
    """Cấu hình đã đọc. Trường rỗng nghĩa là chưa đặt."""

    curseforge_api_key: str = ""
    # Chuông khi game khởi động / thoát / cài xong. Mặc định bật; tắt ở trang CÀI ĐẶT.
    notification_sound: bool = True
    # Blip giao diện (chuyển trang, bấm nút, bung thẻ) kiểu Xbox 360 / Steam Big Picture.
    ui_sound: bool = True
    # Discord Rich Presence: BẬT mặc định. Application ID không còn là việc của người dùng —
    # nó ghim sẵn ở `repo/endpoints.py` (xem `discord_application_id()` dưới đây).
    discord_presence: bool = True
    # Tự kiểm bản mới lúc khởi động (chỉ hỏi GitHub một câu, không tự cài).
    auto_update_check: bool = True
    # Thư mục lưu bản chơi mới (vd ổ còn chỗ). Rỗng = `instances/` trong thư mục dữ liệu.
    default_game_dir_root: str = ""
    # Chỉ giữ để đọc cấu hình cũ; launcher không còn tự ẩn khi game chạy.
    hide_when_game_running: bool = False
    ui_scale: int = 100
    compact_ui: bool = False
    reduced_motion: bool = False
    decorative_background: bool = True
    language: str = "vi"
    # Rỗng: chưa chọn; chỉ runner preview dùng bước thiết lập giao diện.
    interface_style: str = ""


def settings_path(config_dir: Path) -> Path:
    return config_dir / SETTINGS_FILE_NAME


def load_settings(config_dir: Path, environment: Mapping[str, str] | None = None) -> Settings:
    """File hỏng thì coi như rỗng chứ không chặn cả launcher; biến môi trường thắng file."""
    environ = os.environ if environment is None else environment
    settings = Settings()
    path = settings_path(config_dir)
    if path.is_file():
        try:
            fields = as_mapping(read_json(path))
            sound = fields.get("notification_sound")
            ui_sound = fields.get("ui_sound")
            presence = fields.get("discord_presence")
            update_check = fields.get("auto_update_check")
            hide_game = fields.get("hide_when_game_running")
            settings = Settings(
                curseforge_api_key=as_string(fields.get("curseforge_api_key")) or "",
                notification_sound=sound if isinstance(sound, bool) else True,
                ui_sound=ui_sound if isinstance(ui_sound, bool) else True,
                discord_presence=presence if isinstance(presence, bool) else True,
                auto_update_check=update_check if isinstance(update_check, bool) else True,
                default_game_dir_root=(
                    as_string(fields.get("default_game_dir_root")) or ""
                ).strip(),
                hide_when_game_running=hide_game if isinstance(hide_game, bool) else False,
                ui_scale=(as_integer(fields.get("ui_scale")) or 100)
                if fields.get("ui_scale") in (100, 125, 150)
                else 100,
                compact_ui=fields.get("compact_ui") is True,
                reduced_motion=fields.get("reduced_motion") is True,
                decorative_background=fields.get("decorative_background") is not False,
                language="en" if fields.get("language") == "en" else "vi",
                interface_style=as_string(fields.get("interface_style")) or ""
                if fields.get("interface_style") in ("classic", "modern")
                else "",
            )
        except DataFileError:
            settings = Settings()
    env_key = environ.get(CURSEFORGE_KEY_ENV, "").strip()
    if env_key:
        settings = replace(settings, curseforge_api_key=env_key)
    return settings


def discord_application_id(environment: Mapping[str, str] | None = None) -> str:
    """Application ID cho Rich Presence: hằng của dự án, đè được bằng biến môi trường.

    KHÔNG đọc từ `settings.json`: bắt người chơi tự vào Developer Portal tạo app rồi dán id
    vào CÀI ĐẶT là giao việc của launcher cho người dùng — và ai cũng bỏ qua, nên tính năng
    coi như không tồn tại. Ai muốn hiện tên app riêng thì đặt `NOSTALGIA_DISCORD_APP_ID`.
    """
    environ = os.environ if environment is None else environment
    return environ.get(DISCORD_APP_ID_ENV, "").strip() or DISCORD_APPLICATION_ID


def save_settings(config_dir: Path, settings: Settings) -> None:
    """Ghi với quyền 0600: có khoá API bên trong."""
    atomic_write_json(
        settings_path(config_dir),
        {
            "curseforge_api_key": settings.curseforge_api_key.strip(),
            "notification_sound": settings.notification_sound,
            "ui_sound": settings.ui_sound,
            "discord_presence": settings.discord_presence,
            "auto_update_check": settings.auto_update_check,
            "default_game_dir_root": settings.default_game_dir_root.strip(),
            "hide_when_game_running": settings.hide_when_game_running,
            "ui_scale": settings.ui_scale,
            "compact_ui": settings.compact_ui,
            "reduced_motion": settings.reduced_motion,
            "decorative_background": settings.decorative_background,
            "language": settings.language,
            "interface_style": settings.interface_style,
        },
        private=True,
    )
