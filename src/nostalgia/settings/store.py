"""Đọc/ghi `settings.json` trong `config_dir`."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path

from nostalgia.errors import DataFileError
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, read_json

SETTINGS_FILE_NAME = "settings.json"
# Biến môi trường đè lên file: tiện cho CI và cho người không muốn lưu khoá xuống đĩa.
CURSEFORGE_KEY_ENV = "NOSTALGIA_CURSEFORGE_API_KEY"


@dataclass(frozen=True, slots=True)
class Settings:
    """Cấu hình đã đọc. Trường rỗng nghĩa là chưa đặt."""

    curseforge_api_key: str = ""

    @property
    def has_curseforge_key(self) -> bool:
        return bool(self.curseforge_api_key.strip())


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
            settings = Settings(
                curseforge_api_key=as_string(fields.get("curseforge_api_key")) or ""
            )
        except DataFileError:
            settings = Settings()
    env_key = environ.get(CURSEFORGE_KEY_ENV, "").strip()
    if env_key:
        settings = replace(settings, curseforge_api_key=env_key)
    return settings


def save_settings(config_dir: Path, settings: Settings) -> None:
    """Ghi với quyền 0600: có khoá API bên trong."""
    atomic_write_json(
        settings_path(config_dir),
        {"curseforge_api_key": settings.curseforge_api_key.strip()},
        private=True,
    )
