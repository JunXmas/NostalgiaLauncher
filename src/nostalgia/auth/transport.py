"""Ba kiểu request mà luồng đăng nhập cần, dựng trên `HttpClient.send`.

Ở đây chứ không ở `net/http.py`: chỉ đăng nhập mới gửi form và mới cần đọc thân của phản hồi
lỗi. Đẩy chúng vào lớp truyền tải chung là bắt mọi chỗ khác mang theo khái niệm không dùng.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from urllib.parse import urlencode

from nostalgia.model.json_value import JsonValue, as_mapping
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.net.payload import decode_json
from nostalgia.operations.cancellation import CancelToken

FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"
JSON_CONTENT_TYPE = "application/json"


def post_form(
    http_client: HttpClient,
    url: str,
    fields: Mapping[str, str],
    *,
    cancel_token: CancelToken | None = None,
) -> HttpResponse:
    """OAuth của Microsoft nhận tham số dạng form, không phải JSON."""
    return http_client.send(
        "POST",
        url,
        body=urlencode(fields).encode(),
        headers={"Content-Type": FORM_CONTENT_TYPE, "Accept": JSON_CONTENT_TYPE},
        cancel_token=cancel_token,
    )


def post_json(
    http_client: HttpClient,
    url: str,
    document: JsonValue,
    *,
    cancel_token: CancelToken | None = None,
) -> HttpResponse:
    """Xbox Live và Minecraft Services nhận JSON."""
    return http_client.send(
        "POST",
        url,
        body=json.dumps(document).encode(),
        headers={"Content-Type": JSON_CONTENT_TYPE, "Accept": JSON_CONTENT_TYPE},
        cancel_token=cancel_token,
    )


def fetch_with_bearer(
    http_client: HttpClient,
    url: str,
    access_token: str,
    *,
    cancel_token: CancelToken | None = None,
) -> HttpResponse:
    """Hồ sơ người chơi đọc bằng GET kèm vé."""
    return http_client.send(
        "GET",
        url,
        headers={"Authorization": f"Bearer {access_token}", "Accept": JSON_CONTENT_TYPE},
        cancel_token=cancel_token,
    )


def response_fields(response: HttpResponse, *, what: str) -> dict[str, JsonValue]:
    """Đọc thân phản hồi thành đối tượng JSON, kể cả khi mã trả về là lỗi."""
    return as_mapping(decode_json(response.body, what=what))
