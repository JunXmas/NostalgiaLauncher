"""Nạp fixture JSON phiên bản — cắt từ file thật, giữ nguyên cấu trúc.

Ở gốc `tests/` cùng `source_tree.py` và `local_https_server.py`: helper dùng chung thì không
đặt trong `conftest.py` của thư mục con, vì hai `conftest` cùng tên làm bộ kiểm kiểu báo
trùng module.
"""

from __future__ import annotations

import json
from pathlib import Path

from mccore.model.json_value import JsonValue

FIXTURE_DIRECTORY = Path(__file__).resolve().parent / "fixture" / "version"


def load_fixture(version_id: str) -> dict[str, JsonValue]:
    """Đọc fixture theo `version_id`. Đọc file ở đây là đúng chỗ — đây là test, không phải lõi."""
    parsed = json.loads((FIXTURE_DIRECTORY / f"{version_id}.json").read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        message = f"fixture {version_id} phải là đối tượng JSON"
        raise TypeError(message)
    return parsed
