"""Upload + mặc skin trên ely.by qua phiên web (`auth/ely_web.py`).

Trang web làm đúng hai bước này khi người dùng đổi skin: POST multipart vào
``/api/legacy/skins`` (nhận id), rồi PUT ``/api/legacy/users/skin`` với id đó. Ta lặp lại
y nguyên. Nằm ở ``skin/`` chứ không ``auth/``: đăng nhập là việc của auth, còn đây là
nghiệp vụ skin — cùng lý do ``upload.py`` (Mojang) nằm ở đây.
"""

from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin, urlsplit

from nostalgia.auth.ely_web import (
    FORM_CONTENT_TYPE,
    ElyWebSession,
    request_ely_web,
    web_json_body,
)
from nostalgia.errors import AccountError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken

# Trang web từ chối file > 192 KiB (đọc từ app.js: `e.size>196608`); chặn sớm ở đây để
# người dùng nhận câu lỗi tiếng Việt thay vì câu lỗi của server.
MAX_WEB_SKIN_BYTES = 196608


def upload_skin_to_ely(
    http_client: HttpClient,
    web_session: ElyWebSession,
    skin_bytes: bytes,
    filename: str,
    *,
    cancel_token: CancelToken | None = None,
) -> int:
    """Upload PNG vào kho skin ely.by của tài khoản. Trả về ``skinId`` để mặc tiếp."""
    if len(skin_bytes) > MAX_WEB_SKIN_BYTES:
        raise AccountError(
            f"ely.by chỉ nhận skin tới {MAX_WEB_SKIN_BYTES // 1024} KiB — file này "
            f"{len(skin_bytes)} byte"
        )
    boundary = "----NostalgiaElySkinUpload"
    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode()
        + skin_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )
    response = request_ely_web(
        http_client,
        "POST",
        f"{web_session.endpoints.site_root}/api/legacy/skins",
        body=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": web_session.site_cookies,
        },
        cancel_token=cancel_token,
        step="upload skin lên ely.by",
    )
    document = web_json_body(response, step="upload skin lên ely.by")
    _raise_if_site_error(document, step="upload skin lên ely.by")
    skin_id = _find_skin_id(document, web_session.endpoints.site_root)
    if skin_id is None:
        raise AccountError("ely.by nhận skin nhưng không trả id — trang có thể vừa đổi")
    return skin_id


def wear_ely_skin(
    http_client: HttpClient,
    web_session: ElyWebSession,
    skin_id: int,
    *,
    cancel_token: CancelToken | None = None,
) -> None:
    """Mặc một skin đã có trong kho ely.by (bước hai của luồng trang web)."""
    response = request_ely_web(
        http_client,
        "PUT",
        f"{web_session.endpoints.site_root}/api/legacy/users/skin",
        body=urlencode({"skinId": str(skin_id)}).encode(),
        headers={"Content-Type": FORM_CONTENT_TYPE, "Cookie": web_session.site_cookies},
        cancel_token=cancel_token,
        step="mặc skin trên ely.by",
    )
    document = web_json_body(response, step="mặc skin trên ely.by")
    _raise_if_site_error(document, step="mặc skin trên ely.by")


def _raise_if_site_error(document: dict[str, JsonValue], *, step: str) -> None:
    """ely.by trả lỗi dạng ``{"error": "error_login", "text": "..."}`` với HTTP 200."""
    error = as_string(document.get("error"))
    if error and "success" not in error:
        text = re.sub(r"<[^>]+>", "", as_string(document.get("text")) or error)
        raise AccountError(f"{step} thất bại: {text}")


def _find_skin_id(document: dict[str, JsonValue], site_root: str) -> int | None:
    """Frontend dùng url chuyển trang; chỉ lấy ID từ trang skin cùng nguồn Ely.by."""
    extra = as_mapping(document.get("extra"))
    for candidate in (
        as_mapping(document.get("skin")).get("id"),
        document.get("id"),
        as_mapping(extra.get("skin")).get("id"),
        extra.get("id"),
    ):
        if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > 0:
            return candidate
        if isinstance(candidate, str) and candidate.isdigit():
            return int(candidate) if int(candidate) > 0 else None
    location = as_string(document.get("url"))
    if location:
        origin = urlsplit(site_root)
        target = urlsplit(urljoin(site_root.rstrip("/") + "/", location))
        expected_path = re.escape(origin.path.rstrip("/")) + r"/skins/s([1-9]\d*)(?:/edit)?/?"
        match = re.fullmatch(expected_path, target.path)
        if target.scheme == origin.scheme and target.netloc == origin.netloc and match:
            return int(match[1])
    return None
