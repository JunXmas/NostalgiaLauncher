"""Payload tối thiểu của thống kê tự nguyện; không có sự kiện chạy game."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class UsagePayload:
    day: str
    launcher_version: str
    os_group: str
    daily_id: str
    schema_version: Literal[1] = 1
    event: Literal["installation_active"] = "installation_active"

    def json_text(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def usage_sample(launcher_version: str) -> str:
    """Mẫu minh họa cố định, không đọc trạng thái hay mã thật trên máy."""
    return UsagePayload(
        "2026-11-05", launcher_version, "windows", "0123456789abcdef" * 2
    ).json_text()
