"""Phiên web Ely.by: đường duy nhất để ĐỔI skin thật — đăng nhập, upload, mặc.

Route giả dựng đúng hình dạng đã soi từ máy chủ thật (curl 09/2026) và mã nguồn mở
elyby/accounts. Trang thật đổi là các test này không bắt được — đó là hạn chế cố hữu của
việc đi đường web không hợp đồng; bù lại facade luôn ném `AccountError` nêu rõ bước hỏng.
"""

from __future__ import annotations

import json

import pytest

from fake_ely import WEB_JWT, WEB_REFRESH_TOKEN, WEB_SKIN_ID, publish_web
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.auth.ely_web import sign_in_ely_web, web_session_from_refresh_token
from nostalgia.errors import AccountError, TwoFactorRequired
from nostalgia.net.http import HttpClient
from nostalgia.skin.ely_web_upload import (
    MAX_WEB_SKIN_BYTES,
    upload_skin_to_ely,
    wear_ely_skin,
)


def test_sign_in_collects_jwt_cookies_and_refresh_token(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)

    web_session = sign_in_ely_web(http_client, "jun@vi.du", "mat-khau", endpoints=endpoints)

    assert web_session.jwt == WEB_JWT
    assert web_session.refresh_token == WEB_REFRESH_TOKEN
    assert "PHPSESSID=sess-1" in web_session.site_cookies
    assert "remember=rem-1" in web_session.site_cookies
    # Mật khẩu đi tới đúng MỘT nơi: form login của account.ely.by.
    body = server_state.received_body("/elyweb/api/authentication/login").decode()
    assert "mat-khau" in body
    # Bước complete mang JWT, và bước đổi mã mang cookie phiên.
    auth = server_state.received_header("/elyweb/api/oauth2/v1/complete", "Authorization")
    assert auth == f"Bearer {WEB_JWT}"
    cookie = server_state.received_header("/elysite/authorization/oauth", "Cookie")
    assert "PHPSESSID=sess-1" in cookie


def test_session_tokens_never_leak_into_repr(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    web_session = sign_in_ely_web(http_client, "jun@vi.du", "mat-khau", endpoints=endpoints)
    assert WEB_JWT not in repr(web_session)
    assert WEB_REFRESH_TOKEN not in repr(web_session)
    assert "sess-1" not in repr(web_session)


def test_a_totp_error_becomes_two_factor_required(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    server_state.add(
        "/elyweb/api/authentication/login",
        json.dumps({"success": False, "errors": {"totp": "error.totp_required"}}).encode(),
    )
    with pytest.raises(TwoFactorRequired):
        sign_in_ely_web(http_client, "jun@vi.du", "mat-khau", endpoints=endpoints)


def test_wrong_password_is_reported_in_vietnamese(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    server_state.add(
        "/elyweb/api/authentication/login",
        json.dumps({"success": False, "errors": {"password": "error.password_incorrect"}}).encode(),
    )
    with pytest.raises(AccountError, match="từ chối đăng nhập"):
        sign_in_ely_web(http_client, "jun@vi.du", "sai", endpoints=endpoints)


def test_refresh_token_rebuilds_a_session_without_a_password(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)

    web_session = web_session_from_refresh_token(
        http_client, WEB_REFRESH_TOKEN, endpoints=endpoints
    )

    assert web_session.jwt == WEB_JWT
    body = server_state.received_body("/elyweb/api/authentication/refresh-token").decode()
    assert WEB_REFRESH_TOKEN in body


def test_an_expired_refresh_token_asks_for_a_new_login(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    server_state.add(
        "/elyweb/api/authentication/refresh-token",
        json.dumps(
            {"success": False, "errors": {"refresh_token": "error.refresh_token_not_exist"}}
        ).encode(),
    )
    with pytest.raises(AccountError, match="đăng nhập lại"):
        web_session_from_refresh_token(http_client, "het-han", endpoints=endpoints)


def test_upload_sends_multipart_png_and_returns_the_skin_id(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    web_session = sign_in_ely_web(http_client, "jun@vi.du", "mat-khau", endpoints=endpoints)

    skin_id = upload_skin_to_ely(http_client, web_session, b"\x89PNG fake", "skin.png")

    assert skin_id == WEB_SKIN_ID
    body = server_state.received_body("/elysite/api/legacy/skins")
    assert b'name="file"' in body
    assert b"\x89PNG fake" in body
    cookie = server_state.received_header("/elysite/api/legacy/skins", "Cookie")
    assert "PHPSESSID=sess-1" in cookie


def test_an_oversized_skin_is_rejected_before_touching_the_network(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    web_session = sign_in_ely_web(http_client, "jun@vi.du", "mat-khau", endpoints=endpoints)

    with pytest.raises(AccountError, match="KiB"):
        upload_skin_to_ely(http_client, web_session, b"x" * (MAX_WEB_SKIN_BYTES + 1), "to.png")
    assert server_state.request_count("/elysite/api/legacy/skins") == 0


def test_a_site_error_json_with_http_200_still_raises(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """ely.by trả lỗi trong THÂN với HTTP 200 — coi 200 là thành công thì hỏng câm."""
    endpoints = publish_web(server, server_state)
    web_session = sign_in_ely_web(http_client, "jun@vi.du", "mat-khau", endpoints=endpoints)
    server_state.add(
        "/elysite/api/legacy/skins",
        json.dumps(
            {"error": "error_login", "text": 'You need to be <a href="/l">authenticated</a>.'}
        ).encode(),
    )
    with pytest.raises(AccountError, match="authenticated"):
        upload_skin_to_ely(http_client, web_session, b"\x89PNG fake", "skin.png")


def test_wearing_a_skin_puts_its_id_with_the_session_cookie(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish_web(server, server_state)
    web_session = sign_in_ely_web(http_client, "jun@vi.du", "mat-khau", endpoints=endpoints)

    wear_ely_skin(http_client, web_session, WEB_SKIN_ID)

    body = server_state.received_body("/elysite/api/legacy/users/skin").decode()
    assert f"skinId={WEB_SKIN_ID}" in body
