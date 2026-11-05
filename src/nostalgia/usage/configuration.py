"""Chỉ bật dịch vụ sau khi operator xác nhận endpoint đã vận hành."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.errors import NostalgiaError
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.storage.files import read_json


@dataclass(frozen=True, slots=True)
class UsageConfiguration:
    endpoint: str = ""
    ready: bool = False


def load_usage_configuration() -> UsageConfiguration:
    try:
        fields = as_mapping(read_json(Path(__file__).with_name("defaults.json")))
        endpoint = os.environ.get(
            "NOSTALGIA_USAGE_ENDPOINT", as_string(fields.get("endpoint")) or ""
        )
        ready = (
            os.environ.get("NOSTALGIA_USAGE_READY", "1" if fields.get("ready") is True else "0")
            == "1"
        )
        parts = urlsplit(endpoint)
        port = parts.port
        if (
            not ready
            or parts.scheme != "https"
            or not parts.hostname
            or (port is not None and not 1 <= port <= 65535)
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or parts.path != "/v1/usage"
            or any(c.isspace() for c in endpoint)
        ):
            return UsageConfiguration()
        return UsageConfiguration(endpoint, True)
    except (NostalgiaError, OSError, ValueError):
        return UsageConfiguration()
