"""Mã ngày và dấu đã thử gửi; xóa toàn bộ khi từ chối, không có hàng đợi."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import NostalgiaError
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.storage.files import atomic_write_json, read_json


@dataclass(frozen=True, slots=True)
class UsageDay:
    day: str
    daily_id: str
    attempted: bool = False


def load_usage_day(path: Path) -> UsageDay | None:
    try:
        fields = as_mapping(read_json(path))
        day = as_string(fields.get("day")) or ""
        daily_id = as_string(fields.get("daily_id")) or ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) and re.fullmatch(r"[0-9a-f]{32}", daily_id):
            return UsageDay(day, daily_id, fields.get("attempted") is True)
    except (NostalgiaError, OSError):
        pass
    return None


def save_usage_day(path: Path, state: UsageDay) -> None:
    atomic_write_json(
        path,
        {"day": state.day, "daily_id": state.daily_id, "attempted": state.attempted},
        private=True,
    )
