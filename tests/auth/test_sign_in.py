"""Bốn chặng đăng nhập.

Mỗi chặng phải đưa đúng thứ chặng sau cần, và mọi nhánh hỏng phải nói rõ việc người dùng
phải làm chứ không chỉ ném ra một mã số.
"""

from __future__ import annotations

import json

import pytest

from fake_microsoft import (
    MICROSOFT_ACCESS_TOKEN,
    MINECRAFT_TOKEN,
    PLAYER_NAME,
    PLAYER_UUID_UNDASHED,
    REFRESH_TOKEN,
    USER_CODE,
    USER_HASH,
    VERIFICATION_URL,
    body,
    publish,
)
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.auth.device_code import DeviceCode
from nostalgia.auth.microsoft import sign_in
from nostalgia.auth.minecraft import to_dashed_uuid
from nostalgia.errors import AuthError
from nostalgia.net.http import HttpClient

CLIENT_ID = "ma-ung-dung-gia"
DASHED_UUID = "b50ad385-829d-3141-a216-7e7d7539ba7f"


def test_a_full_sign_in_walks_all_four_stages(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish(server, server_state)
    seen: list[DeviceCode] = []

    login = sign_in(http_client, CLIENT_ID, seen.append, endpoints=endpoints, sleep_seconds=0.0)

    assert [code.user_code for code in seen] == [USER_CODE]
    assert seen[0].verification_url == VERIFICATION_URL
    assert login.minecraft_session.owns_game
    assert login.minecraft_session.player_name == PLAYER_NAME
    assert login.minecraft_session.player_uuid == DASHED_UUID, "kho tài khoản lưu UUID có gạch"
    assert login.minecraft_session.access_token == MINECRAFT_TOKEN
    assert login.tokens.refresh_token == REFRESH_TOKEN


def test_every_stage_receives_what_the_next_one_needs(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Sai một trường trong thân request là hỏng theo kiểu chỉ máy chủ thật mới thấy."""
    endpoints = publish(server, server_state)

    sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)

    assert f"d={MICROSOFT_ACCESS_TOKEN}" in server_state.received_body("/xbox").decode()
    assert "http://auth.xboxlive.com" in server_state.received_body("/xbox").decode()
    xsts_sent = json.loads(server_state.received_body("/xsts"))
    assert xsts_sent["Properties"]["UserTokens"] == ["ve-xbox"]
    assert xsts_sent["RelyingParty"] == "rp://api.minecraftservices.com/"
    login_sent = json.loads(server_state.received_body("/mc-login"))
    assert login_sent["identityToken"] == f"XBL3.0 x={USER_HASH};ve-xsts"
    assert (
        server_state.received_header("/mc-profile", "Authorization") == f"Bearer {MINECRAFT_TOKEN}"
    )


def test_the_first_request_asks_for_an_offline_token_as_a_form(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """OAuth của Microsoft nhận form, không nhận JSON — gửi sai kiểu là 400 khó hiểu.

    Và thiếu `offline_access` thì không có refresh token, tức mỗi lần chơi lại phải nhập mã.
    """
    endpoints = publish(server, server_state)

    sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)

    sent = server_state.received_body("/devicecode").decode()
    assert "scope=XboxLive.signin+offline_access" in sent
    assert f"client_id={CLIENT_ID}" in sent
    assert (
        server_state.received_header("/devicecode", "Content-Type")
        == "application/x-www-form-urlencoded"
    )


def test_the_user_hash_comes_from_xbox_live_not_from_xsts(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """XSTS trả lại một `uhs` khác; dùng nhầm nó là 401 ở chặng cuối, rất khó truy."""
    endpoints = publish(server, server_state)
    server_state.add(
        "/xsts", body({"Token": "ve-xsts", "DisplayClaims": {"xui": [{"uhs": "SAI"}]}})
    )

    sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)

    assert f"x={USER_HASH};" in json.loads(server_state.received_body("/mc-login"))["identityToken"]


def test_an_account_without_the_game_signs_in_as_demo(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """404 ở hồ sơ KHÔNG phải lỗi — tài khoản hợp lệ, chỉ là chưa mua game."""
    endpoints = publish(server, server_state)
    server_state.add("/mc-profile", b"", status=404)

    login = sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)

    assert not login.minecraft_session.owns_game
    assert login.minecraft_session.access_token == MINECRAFT_TOKEN
    assert login.minecraft_session.player_name == ""


def test_an_unapproved_azure_app_says_where_to_apply(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """403 ở đây không phải sai mã hay sai vé — app chưa được Microsoft duyệt."""
    endpoints = publish(server, server_state)
    server_state.add("/mc-login", b"", status=403)

    with pytest.raises(AuthError, match="mce-reviewappid"):
        sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)


@pytest.mark.parametrize(
    ("xerr", "expected"),
    [
        ("2148916233", "hồ sơ Xbox"),
        ("2148916235", "quốc gia"),
        ("2148916238", "trẻ em"),
    ],
)
def test_each_xsts_refusal_explains_what_the_user_must_do(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    xerr: str,
    expected: str,
) -> None:
    endpoints = publish(server, server_state)
    server_state.add("/xsts", body({"XErr": int(xerr)}), status=401)

    with pytest.raises(AuthError, match=expected):
        sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)


def test_an_unknown_xsts_code_still_reports_the_number(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish(server, server_state)
    server_state.add("/xsts", body({"XErr": 999}), status=401)

    with pytest.raises(AuthError, match="999"):
        sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)


def test_the_uuid_is_normalised_to_the_dashed_form() -> None:
    """Mojang trả không gạch; kho tài khoản lưu có gạch để hai loại tài khoản nhìn giống nhau."""
    assert to_dashed_uuid(PLAYER_UUID_UNDASHED) == DASHED_UUID
    assert to_dashed_uuid(DASHED_UUID) == DASHED_UUID, "đã có gạch thì giữ nguyên"
    assert to_dashed_uuid("khong-phai-uuid") == "khong-phai-uuid"
