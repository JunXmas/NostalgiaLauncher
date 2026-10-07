"""Địa chỉ dịch vụ công khai; không lưu OAuth secret hoặc khóa thanh toán trong launcher."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.errors import NostalgiaError, SocialError
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, read_json


@dataclass(frozen=True, slots=True)
class ServiceConfiguration:
    account_url: str = ""
    room_sync_url: str = ""


def verify_service_url(value: str) -> str:
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as error:
        raise SocialError("Origin HTTPS không hợp lệ.") from error
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or (port is not None and not 1 <= port <= 65535)
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
        or any(letter.isspace() for letter in value)
    ):
        raise SocialError("Dịch vụ cần origin HTTPS, không có tài khoản, đường dẫn hoặc query.")
    return value.rstrip("/")


def read_configuration(config_dir: Path) -> ServiceConfiguration:
    defaults = as_mapping(read_json(Path(__file__).with_name("service-defaults.json")))
    path = config_dir / "services.json"
    try:
        fields = as_mapping(read_json(path)) if path.exists() else {}
    except (NostalgiaError, OSError, ValueError):
        fields = {}
    return ServiceConfiguration(
        verify_service_url(
            os.environ.get(
                "NOSTALGIA_ACCOUNT_URL",
                as_string(defaults.get("account_url"))
                or as_string(fields.get("account_url"))
                or "",
            )
        ),
        verify_service_url(
            os.environ.get(
                "NOSTALGIA_ROOM_SYNC_URL",
                as_string(defaults.get("room_sync_url"))
                or as_string(fields.get("room_sync_url"))
                or "",
            )
        ),
    )


def save_configuration(config_dir: Path, configuration: ServiceConfiguration) -> None:
    atomic_write_json(
        config_dir / "services.json",
        {
            "account_url": verify_service_url(configuration.account_url),
            "room_sync_url": verify_service_url(configuration.room_sync_url),
        },
    )


def load_configuration(config_dir: Path) -> ServiceConfiguration:
    try:
        return read_configuration(config_dir)
    except (NostalgiaError, OSError, ValueError):
        logging.warning("Cấu hình dịch vụ không hợp lệ; hãy cập nhật launcher.")
        return ServiceConfiguration()
