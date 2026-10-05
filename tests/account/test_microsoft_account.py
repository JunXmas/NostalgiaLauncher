"""Lưu tài khoản Microsoft và giữ nó còn hiệu lực — thời gian là đối số, không phải đồng hồ."""

from __future__ import annotations

from pathlib import Path

import pytest

from fake_microsoft import PLAYER_NAME, REFRESH_TOKEN, body, publish
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.microsoft import (
    REFRESH_MARGIN_SECONDS,
    build_microsoft_account,
    needs_refresh,
    refresh_account,
)
from nostalgia.account.model import MICROSOFT, OFFLINE, Account
from nostalgia.account.offline import build_offline_account
from nostalgia.account.store import load_accounts, save_accounts
from nostalgia.auth.microsoft import sign_in
from nostalgia.errors import AuthError
from nostalgia.net.http import HttpClient

CLIENT_ID = "ma-ung-dung-gia"
NOW = 1_000_000.0
DASHED_UUID = "b50ad385-829d-3141-a216-7e7d7539ba7f"


def sign_in_once(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> Account:
    endpoints = publish(server, server_state)
    login = sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)
    return build_microsoft_account(login, now=NOW)


def test_a_signed_in_account_carries_everything_needed_to_play_again(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    account = sign_in_once(server, server_state, http_client)

    assert account.player_name == PLAYER_NAME
    assert account.player_uuid == DASHED_UUID
    assert account.account_kind == MICROSOFT
    assert account.refresh_token == REFRESH_TOKEN
    assert account.expires_at == NOW + 3600


def test_an_account_without_the_game_is_still_worth_saving(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Lần sau họ không phải đăng nhập lại chỉ để biết mình vẫn chưa mua game."""
    endpoints = publish(server, server_state)
    server_state.add("/mc-profile", b"", status=404)

    login = sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)
    account = build_microsoft_account(login, now=NOW)

    assert account.player_name == "Demo"
    assert account.refresh_token == REFRESH_TOKEN


def test_both_tokens_survive_the_round_trip_to_disk(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    account = sign_in_once(server, server_state, http_client)
    path = tmp_path / "accounts.json"

    save_accounts(path, (account,))

    assert load_accounts(path) == (account,)


def test_a_record_with_a_broken_expiry_still_loads(tmp_path: Path) -> None:
    """Giá trị lạ không được làm bay cả bản ghi — mất tài khoản vì một trường hỏng là quá đắt."""
    import json

    path = tmp_path / "accounts.json"
    path.write_text(
        json.dumps(
            {
                "accounts": [
                    {
                        "player_name": "Jun",
                        "player_uuid": "u",
                        "account_kind": MICROSOFT,
                        "expires_at": "hôm qua",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    accounts = load_accounts(path)

    assert accounts[0].player_name == "Jun"
    assert accounts[0].expires_at == 0.0


def test_the_refresh_token_never_shows_up_in_repr() -> None:
    """Vé làm mới sống hàng tháng: lộ nó là mất tài khoản, không chỉ mất một phiên."""
    account = Account(
        player_name="Jun",
        player_uuid="u",
        account_kind=MICROSOFT,
        access_token="ve-choi",
        refresh_token="ve-lam-moi-rat-quy",
    )

    assert "ve-lam-moi-rat-quy" not in repr(account)
    assert "ve-choi" not in repr(account)
    assert repr(account).count("***") == 2


def test_an_offline_account_never_needs_refreshing() -> None:
    account = build_offline_account("Jun")
    assert account.account_kind == OFFLINE
    assert not needs_refresh(account, now=NOW)
    assert not needs_refresh(account, now=NOW + 10**9)


def test_a_fresh_token_is_left_alone_but_a_stale_one_is_not() -> None:
    account = Account(
        player_name="Jun",
        player_uuid="u",
        account_kind=MICROSOFT,
        refresh_token="r",
        expires_at=NOW + 3600,
    )

    assert not needs_refresh(account, now=NOW)
    assert needs_refresh(account, now=NOW + 3600), "quá hạn thì phải làm mới"


def test_refreshing_starts_before_the_token_actually_dies() -> None:
    """Hết hạn giữa lúc game đang khởi động là một màn hình lỗi chẳng liên quan tới đăng nhập."""
    account = Account(
        player_name="Jun",
        player_uuid="u",
        account_kind=MICROSOFT,
        refresh_token="r",
        expires_at=NOW + REFRESH_MARGIN_SECONDS - 1,
    )

    assert needs_refresh(account, now=NOW)


def test_an_account_with_no_known_expiry_is_refreshed() -> None:
    """Thà tốn một vòng gọi còn hơn khởi động game với vé đã chết."""
    account = Account(player_name="Jun", player_uuid="u", account_kind=MICROSOFT, refresh_token="r")
    assert needs_refresh(account, now=NOW)


def test_refreshing_replaces_the_tokens_and_pushes_the_expiry_out(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish(server, server_state)
    stale = Account(
        player_name="Jun",
        player_uuid="u",
        account_kind=MICROSOFT,
        access_token="ve-cu",
        refresh_token=REFRESH_TOKEN,
        expires_at=NOW - 1,
    )

    refreshed = refresh_account(http_client, CLIENT_ID, stale, now=NOW, endpoints=endpoints)

    assert refreshed.access_token != "ve-cu"
    assert refreshed.expires_at == NOW + 3600
    assert not needs_refresh(refreshed, now=NOW)
    assert server_state.request_count("/devicecode") == 0, "không được bắt nhập mã lại"


def test_a_dead_refresh_token_asks_for_a_new_sign_in(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish(server, server_state)
    server_state.add("/token", body({"error": "invalid_grant"}), status=400)
    account = Account(
        player_name="Jun", player_uuid="u", account_kind=MICROSOFT, refresh_token="ve-chet"
    )

    with pytest.raises(AuthError, match="đăng nhập lại"):
        refresh_account(http_client, CLIENT_ID, account, now=NOW, endpoints=endpoints)


def test_an_account_without_a_refresh_token_says_so_instead_of_calling_out(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    endpoints = publish(server, server_state)
    account = Account(player_name="Jun", player_uuid="u", account_kind=MICROSOFT)

    with pytest.raises(AuthError, match="đăng nhập lại"):
        refresh_account(http_client, CLIENT_ID, account, now=NOW, endpoints=endpoints)

    assert server_state.request_count("/token") == 0


def test_a_demo_account_keeps_its_saved_name_after_refreshing(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    """Danh sách tài khoản không được đột nhiên đổi tên sau một lần làm mới."""
    endpoints = publish(server, server_state)
    server_state.add("/mc-profile", b"", status=404)
    account = Account(
        player_name="TenDaDat",
        player_uuid="u",
        account_kind=MICROSOFT,
        refresh_token=REFRESH_TOKEN,
    )

    refreshed = refresh_account(http_client, CLIENT_ID, account, now=NOW, endpoints=endpoints)

    assert refreshed.player_name == "TenDaDat"
    assert refreshed.refresh_token == REFRESH_TOKEN


def test_a_demo_account_gets_a_uuid_so_the_store_can_read_it_back(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """Không có UUID thì kho từ chối chính bản ghi vừa lưu — lưu được mà đọc lại là mất.

    Lệnh khởi động cũng cần một UUID, kể cả ở bản dùng thử.
    """
    endpoints = publish(server, server_state)
    server_state.add("/mc-profile", b"", status=404)
    login = sign_in(http_client, CLIENT_ID, endpoints=endpoints, sleep_seconds=0.0)

    account = build_microsoft_account(login, now=NOW)
    path = tmp_path / "accounts.json"
    save_accounts(path, (account,))

    assert account.player_uuid, "tài khoản demo vẫn phải có UUID"
    assert load_accounts(path) == (account,), "phải đọc lại được đúng bản đã lưu"
