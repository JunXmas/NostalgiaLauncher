"""Biến thân phản hồi thành JSON, và nói rõ *tài liệu nào* hỏng khi nó hỏng.

Tách khỏi `http.py` vì đây là việc **giải mã**, không phải việc **truyền tải**. Ranh giới đó
cũng giữ cho `http.py` không phình: nó chỉ biết gửi và nhận byte.

`JSONDecodeError` trần chỉ nói dòng và cột. Với năm nguồn JSON khác nhau (danh mục phiên
bản, JSON phiên bản, hai tầng manifest bản Java, và các chặng đăng nhập Microsoft) thì thông
báo đó không đủ để lần ra chỗ hỏng.
"""

from __future__ import annotations

import json

from nostalgia.errors import DataFileError
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import HttpClient


def decode_json(payload: bytes, *, what: str) -> JsonValue:
    """Giải mã một thân phản hồi đã đọc trọn."""
    try:
        # json.loads khai trả `Any`; ép về JsonValue ngay tại biên để cái `Any` đó không
        # lan ra khắp nơi dùng sau.
        document: JsonValue = json.loads(payload)
    except json.JSONDecodeError as exc:
        message = f"{what} không phải JSON hợp lệ: {exc}"
        raise DataFileError(message) from exc
    return document


def fetch_json(http_client: HttpClient, url: str, *, what: str) -> JsonValue:
    """Tải một tài liệu JSON. Ném lỗi nếu mã trả về không phải 2xx."""
    return decode_json(http_client.fetch_bytes(url), what=what)
