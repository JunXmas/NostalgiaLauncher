"""Biến thân phản hồi thành JSON, và nói rõ *tài liệu nào* hỏng khi nó hỏng.

Tách khỏi `http.py` vì đây là việc **giải mã**, không phải việc **truyền tải**. Ranh giới đó
cũng giữ cho `http.py` không phình: nó chỉ biết gửi và nhận byte.

`JSONDecodeError` trần chỉ nói dòng và cột. Với năm nguồn JSON khác nhau (danh mục phiên
bản, JSON phiên bản, hai tầng manifest bản Java, và các chặng đăng nhập Microsoft) thì thông
báo đó không đủ để lần ra chỗ hỏng.
"""

from __future__ import annotations

import json

from nostalgia.errors import DataFileError, NetworkError
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import DEFAULT_MAX_RESPONSE_BYTES, HttpClient
from nostalgia.operations.cancellation import CancelToken


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


def fetch_json(
    http_client: HttpClient,
    url: str,
    *,
    what: str,
    max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    cancel_token: CancelToken | None = None,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
) -> JsonValue:
    """Tải một tài liệu JSON (POST nếu có `body`). Ném `NetworkError` khi mã không phải 2xx.

    Một hàm dùng chung cho Mojang, Fabric/Quilt, Forge, Modrinth: mỗi nguồn chỉ khác nhau
    header và trần dung lượng, không đáng mỗi module một bản chép.
    """
    request_headers = dict(headers or {})
    request_headers.setdefault("Accept", "application/json")
    if body is not None:
        request_headers.setdefault("Content-Type", "application/json")
    response = http_client.send(
        "POST" if body is not None else "GET",
        url,
        body=body,
        headers=request_headers,
        max_bytes=max_bytes,
        cancel_token=cancel_token,
    )
    if not response.is_ok:
        message = f"{what} trả {response.status} cho {url}"
        raise NetworkError(message)
    return decode_json(response.body, what=what)
