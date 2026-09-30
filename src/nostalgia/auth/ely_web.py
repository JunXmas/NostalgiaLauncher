"""Phiên web Ely.by — thứ cho phép ĐỔI skin thật từ launcher.

Ely.by không có API công khai để upload skin: OAuth2 của họ chỉ có 4 scope đọc
(account_info, account_email, offline_access, minecraft_server_session), còn Yggdrasil
(authserver.ely.by/auth) chỉ phát vé chơi game. Đường duy nhất là đường chính người dùng đi
trên trình duyệt, và ta đi ĐÚNG đường đó với cùng thông tin đăng nhập họ đã gõ vào launcher:

    1. POST account.ely.by/api/authentication/login {login, password[, totp]}
       → JWT ``access_token`` (soi từ mã nguồn mở elyby/accounts, AuthenticationController).
    2. GET  ely.by/authorization/login → 302 sang account.ely.by/oauth2/v1/ely?…&state=…
       (lấy PHPSESSID của ely.by + state do chính ely.by phát — không tự bịa).
    3. POST account.ely.by/api/oauth2/v1/complete?… (Bearer JWT, body ``accept=1``)
       → ``redirectUri`` chứa ``code`` (client "ely" là client chính chủ, auto-approve).
    4. GET  ely.by/authorization/oauth?code=…&state=… với cookie PHPSESSID
       → phiên web ely.by sẵn sàng.
    5. POST ely.by/api/legacy/skins (multipart ``file``) — upload; hoặc
       POST ely.by/api/legacy/skins/from-url {url}. Rồi POST /api/legacy/users/skin
       {skinId} để MẶC skin đó (trang web làm đúng hai bước này).

Mật khẩu chỉ đi thẳng tới account.ely.by qua TLS — như khi đăng nhập Yggdrasil — và không
được lưu; cái được giữ trong RAM suốt thao tác là JWT + cookie phiên, hết thao tác là bỏ.

Đây là đường không có hợp đồng ổn định (frontend đổi là gãy), nên mọi bước đều ném
``AccountError`` với thông điệp nêu rõ bước hỏng, và người gọi luôn còn lối thoát: mở
ely.by trên trình duyệt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

from nostalgia.errors import AccountError, DataFileError, NetworkError, TwoFactorRequired
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.net.payload import decode_json
from nostalgia.operations.cancellation import CancelToken

logger = logging.getLogger(__name__)

FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


@dataclass(frozen=True, slots=True)
class ElyWebEndpoints:
    """Hai gốc địa chỉ tách rời để test trỏ cả hai về máy chủ giả.

    Nằm ở đây (không trong ``AuthEndpoints``) vì chỉ luồng đổi skin cần; ``SkinOperations``
    dựng nó từ ``AuthEndpoints.ely_web_account_root``/``ely_web_site_root``.
    """

    account_root: str = "https://account.ely.by"
    site_root: str = "https://ely.by"


DEFAULT_ELY_WEB_ENDPOINTS = ElyWebEndpoints()


@dataclass(frozen=True, slots=True)
class ElyWebSession:
    """Phiên đã đăng nhập: JWT của account.ely.by + cookie của ely.by.

    JWT và cookie chỉ sống trong RAM suốt một thao tác. ``refresh_token`` là thứ DUY NHẤT
    đáng lưu xuống đĩa (vào ``Account.refresh_token``, vốn để trống với Ely): lần đổi skin
    sau đổi nó lấy JWT mới qua ``web_session_from_refresh_token`` — khỏi hỏi lại mật khẩu.
    """

    endpoints: ElyWebEndpoints
    jwt: str
    site_cookies: str  # "PHPSESSID=…; remember=…" — gửi nguyên trong header Cookie
    refresh_token: str = ""

    def __repr__(self) -> str:  # JWT, cookie, refresh token đều là vé — không cho rơi vào log
        return "ElyWebSession(jwt='***', site_cookies='***', refresh_token='***')"


def _header_values(response: HttpResponse, header_name: str) -> tuple[str, ...]:
    """Mọi giá trị của một header, khớp tên không phân biệt hoa thường. KHÔNG gộp:
    `Set-Cookie` xuất hiện nhiều lần, gộp bằng dấu phẩy là phá giá trị (Expires có phẩy)."""
    folded = header_name.casefold()
    return tuple(value for key, value in response.headers if key.casefold() == folded)


def _collect_cookies(response: HttpResponse, jar: dict[str, str]) -> None:
    for set_cookie in _header_values(response, "Set-Cookie"):
        first = set_cookie.split(";", 1)[0]
        name, _, value = first.partition("=")
        if name.strip():
            jar[name.strip()] = value.strip()


def _cookie_header(jar: dict[str, str]) -> str:
    return "; ".join(f"{name}={value}" for name, value in jar.items())


def sign_in_ely_web(
    http_client: HttpClient,
    email_or_name: str,
    password: str,
    *,
    totp_code: str = "",
    endpoints: ElyWebEndpoints = DEFAULT_ELY_WEB_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> ElyWebSession:
    """CHẠM MẠNG. Đăng nhập account.ely.by rồi hoàn tất OAuth nội bộ để có phiên ely.by."""
    jwt, refresh_token = _login_jwt(
        http_client, email_or_name, password, totp_code, endpoints, cancel_token
    )
    return _session_from_jwt(http_client, jwt, refresh_token, endpoints, cancel_token)


def web_session_from_refresh_token(
    http_client: HttpClient,
    refresh_token: str,
    *,
    endpoints: ElyWebEndpoints = DEFAULT_ELY_WEB_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> ElyWebSession:
    """CHẠM MẠNG. Dựng lại phiên web từ refresh token đã lưu — không cần mật khẩu."""
    response = request_ely_web(
        http_client,
        "POST",
        f"{endpoints.account_root}/api/authentication/refresh-token",
        body=urlencode({"refresh_token": refresh_token}).encode(),
        headers={"Content-Type": FORM_CONTENT_TYPE},
        cancel_token=cancel_token,
        step="làm mới phiên account.ely.by",
    )
    document = web_json_body(response, step="làm mới phiên account.ely.by")
    jwt = as_string(document.get("access_token"))
    if not document.get("success") or not jwt:
        raise AccountError("phiên Ely.by đã hết hạn — cần đăng nhập lại để đổi skin")
    return _session_from_jwt(http_client, jwt, refresh_token, endpoints, cancel_token)


def _session_from_jwt(
    http_client: HttpClient,
    jwt: str,
    refresh_token: str,
    endpoints: ElyWebEndpoints,
    cancel_token: CancelToken | None,
) -> ElyWebSession:
    jar: dict[str, str] = {}
    authorize_url = _start_site_login(http_client, endpoints, jar, cancel_token)
    redirect_uri = _complete_oauth(http_client, jwt, authorize_url, endpoints, cancel_token)
    _finish_site_login(http_client, redirect_uri, jar, cancel_token)
    return ElyWebSession(
        endpoints=endpoints,
        jwt=jwt,
        site_cookies=_cookie_header(jar),
        refresh_token=refresh_token,
    )


def _login_jwt(
    http_client: HttpClient,
    email_or_name: str,
    password: str,
    totp_code: str,
    endpoints: ElyWebEndpoints,
    cancel_token: CancelToken | None,
) -> tuple[str, str]:
    fields = {"login": email_or_name, "password": password, "rememberMe": "1"}
    if totp_code.strip():
        fields["totp"] = totp_code.strip()
    response = request_ely_web(
        http_client,
        "POST",
        f"{endpoints.account_root}/api/authentication/login",
        body=urlencode(fields).encode(),
        headers={"Content-Type": FORM_CONTENT_TYPE},
        cancel_token=cancel_token,
        step="đăng nhập account.ely.by",
    )
    document = web_json_body(response, step="đăng nhập account.ely.by")
    if not document.get("success"):
        errors = as_mapping(document.get("errors"))
        if "totp" in errors:
            raise TwoFactorRequired("tài khoản Ely.by này bật 2FA — cần mã từ ứng dụng")
        detail = ", ".join(as_string(v) or str(v) for v in errors.values()) or "không rõ lý do"
        raise AccountError(f"Ely.by từ chối đăng nhập: {detail}")
    access_token = as_string(document.get("access_token"))
    if not access_token:
        raise AccountError("Ely.by trả lời thiếu access_token — trang có thể vừa đổi")
    return access_token, as_string(document.get("refresh_token")) or ""


def _start_site_login(
    http_client: HttpClient,
    endpoints: ElyWebEndpoints,
    jar: dict[str, str],
    cancel_token: CancelToken | None,
) -> str:
    """GET ely.by/authorization/login: nhận PHPSESSID và URL authorize kèm ``state``."""
    response = request_ely_web(
        http_client,
        "GET",
        f"{endpoints.site_root}/authorization/login",
        cancel_token=cancel_token,
        step="mở phiên ely.by",
    )
    _collect_cookies(response, jar)
    locations = _header_values(response, "Location")
    if not locations:
        raise AccountError("ely.by không chuyển hướng sang trang authorize — trang có thể vừa đổi")
    return locations[0]


def _complete_oauth(
    http_client: HttpClient,
    jwt: str,
    authorize_url: str,
    endpoints: ElyWebEndpoints,
    cancel_token: CancelToken | None,
) -> str:
    query = urlsplit(authorize_url).query
    response = request_ely_web(
        http_client,
        "POST",
        f"{endpoints.account_root}/api/oauth2/v1/complete?{query}",
        body=b"accept=1",
        headers={"Content-Type": FORM_CONTENT_TYPE, "Authorization": f"Bearer {jwt}"},
        cancel_token=cancel_token,
        step="duyệt OAuth nội bộ Ely.by",
    )
    document = web_json_body(response, step="duyệt OAuth nội bộ Ely.by")
    redirect_uri = as_string(document.get("redirectUri"))
    if not document.get("success") or not redirect_uri:
        raise AccountError(f"Ely.by không phát mã đăng nhập web (HTTP {response.status})")
    return redirect_uri


def _finish_site_login(
    http_client: HttpClient,
    redirect_uri: str,
    jar: dict[str, str],
    cancel_token: CancelToken | None,
) -> None:
    response = request_ely_web(
        http_client,
        "GET",
        redirect_uri,
        headers={"Cookie": _cookie_header(jar)},
        cancel_token=cancel_token,
        step="hoàn tất đăng nhập ely.by",
    )
    _collect_cookies(response, jar)
    # Thành công là 302 về trang chủ; 200 kèm trang lỗi cũng có thể xảy ra nếu state lệch.
    if response.status >= 400:
        raise AccountError(f"ely.by từ chối mã đăng nhập web (HTTP {response.status})")


def request_ely_web(
    http_client: HttpClient,
    method: str,
    url: str,
    *,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    cancel_token: CancelToken | None,
    step: str,
) -> HttpResponse:
    """Một request của luồng web Ely: lỗi đường truyền thành `AccountError` nêu rõ bước."""
    try:
        return http_client.send(method, url, body=body, headers=headers, cancel_token=cancel_token)
    except NetworkError as exc:
        raise AccountError(f"{step}: không gọi được máy chủ ({exc})") from exc


def web_json_body(response: HttpResponse, *, step: str) -> dict[str, JsonValue]:
    """Thân JSON dạng mapping; ely.by trả thứ khác nghĩa là trang vừa đổi — báo rõ bước."""
    try:
        document = decode_json(response.body, what=step)
    except DataFileError as exc:
        raise AccountError(
            f"{step}: máy chủ trả HTTP {response.status} không phải JSON — trang có thể vừa đổi"
        ) from exc
    if not isinstance(document, dict):
        raise AccountError(f"{step}: máy chủ trả JSON không đúng dạng")
    return document
