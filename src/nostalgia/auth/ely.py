"""Đăng nhập Ely.by — máy chủ Yggdrasil cho tài khoản non-premium.

    POST /auth/authenticate {username, password, clientToken, requestUser}
      → {accessToken, clientToken, selectedProfile: {id, name}}
    POST /auth/refresh {accessToken, clientToken} → cặp vé mới
    POST /auth/validate {accessToken, clientToken} → 204 nếu còn dùng được

Tài khoản bật 2FA gửi mật khẩu dạng `mật_khẩu:mã_TOTP`; thiếu mã thì server trả 401 với
thông báo "two factor" — ta đổi thành lỗi riêng để giao diện hỏi mã.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS, AuthEndpoints
from nostalgia.auth.minecraft import to_dashed_uuid
from nostalgia.auth.transport import post_json, response_fields
from nostalgia.errors import AuthError, TwoFactorRequired
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


@dataclass(frozen=True, slots=True)
class ElyLogin:
    player_name: str
    player_uuid: str
    access_token: str
    client_token: str

    def __repr__(self) -> str:
        return f"ElyLogin(player_name={self.player_name!r}, player_uuid={self.player_uuid!r})"


def sign_in_ely(
    http_client: HttpClient,
    email_or_name: str,
    password: str,
    *,
    totp_code: str = "",
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> ElyLogin:
    """CHẠM MẠNG. Mật khẩu không được lưu ở đâu; chỉ giữ accessToken + clientToken."""
    client_token = secrets.token_hex(16)
    secret = f"{password}:{totp_code.strip()}" if totp_code.strip() else password
    response = post_json(
        http_client,
        f"{endpoints.ely_auth_url}/authenticate",
        {
            "username": email_or_name,
            "password": secret,
            "clientToken": client_token,
            "requestUser": False,
        },
        cancel_token=cancel_token,
    )
    if not response.is_ok:
        raise _describe_failure(response.body)
    return _parse_login(response_fields(response, what="Ely.by authenticate"), client_token)


def refresh_ely(
    http_client: HttpClient,
    access_token: str,
    client_token: str,
    *,
    endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> ElyLogin:
    """CHẠM MẠNG. Vé mới cho lần chạy này; vé cũ hết giá trị."""
    response = post_json(
        http_client,
        f"{endpoints.ely_auth_url}/refresh",
        {"accessToken": access_token, "clientToken": client_token, "requestUser": False},
        cancel_token=cancel_token,
    )
    if not response.is_ok:
        message = "vé Ely.by hết hạn — đăng nhập lại tài khoản này"
        raise AuthError(message)
    return _parse_login(response_fields(response, what="Ely.by refresh"), client_token)


def _parse_login(fields: dict[str, JsonValue], client_token: str) -> ElyLogin:
    selected = as_mapping(fields.get("selectedProfile"))
    player_name = as_string(selected.get("name")) or ""
    undashed = as_string(selected.get("id")) or ""
    access_token = as_string(fields.get("accessToken")) or ""
    if not (player_name and undashed and access_token):
        message = "Ely.by trả hồ sơ thiếu tên, id hoặc vé"
        raise AuthError(message)
    return ElyLogin(player_name, to_dashed_uuid(undashed), access_token, client_token)


def _describe_failure(body: bytes) -> AuthError:
    text = body.decode("utf-8", "replace")
    lowered = text.lower()
    if "two factor" in lowered or "totp" in lowered:
        return TwoFactorRequired("tài khoản bật xác thực hai lớp: nhập mã từ ứng dụng TOTP")
    if "invalid credentials" in lowered or "ForbiddenOperationException" in text:
        return AuthError("Ely.by từ chối: sai email/tên hoặc mật khẩu")
    return AuthError(f"Ely.by trả lỗi: {text[:160]}")
