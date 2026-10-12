"""Khôi phục phiên đúng tài khoản; chỉ thành công khi có phiên đổi skin sử dụng được."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_ely_upload import SKIN_PNG, make_ely_web_launcher

import fake_ely
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import ELY, Account
from nostalgia.account.store import save_accounts
from nostalgia.api import Launcher
from nostalgia.errors import AccountError, TwoFactorRequired


@pytest.fixture
def ely_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> Launcher:
    return make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)


def old_account(launcher: Launcher) -> Account:
    account = Account(fake_ely.ELY_NAME, fake_ely.ELY_UUID, ELY, "old-game-ticket")
    save_accounts(launcher.paths.accounts_json, (account,))
    return account


def test_old_account_can_renew_and_upload_without_removing_it(
    ely_launcher: Launcher,
    server_state: ServerState,
    tmp_path: Path,
) -> None:
    account = old_account(ely_launcher)
    renewed = ely_launcher.renew_ely_web_session(account.account_id, "jun@example.com", "secret")
    assert renewed.account_id == account.account_id
    assert ely_launcher.list_accounts() == (renewed,)
    assert renewed.refresh_token == fake_ely.WEB_REFRESH_TOKEN
    assert "secret" not in ely_launcher.paths.accounts_json.read_text()
    path = tmp_path / "skin.png"
    path.write_bytes(SKIN_PNG)
    server_state.add(f"/ely/skins/{fake_ely.ELY_NAME}.png", SKIN_PNG)
    ely_launcher.upload_skin_to_ely(renewed, path)
    assert SKIN_PNG in server_state.received_body("/elysite/api/legacy/skins")
    assert (
        f"skinId={fake_ely.WEB_SKIN_ID}"
        in server_state.received_body("/elysite/api/legacy/users/skin").decode()
    )


def test_signing_in_as_someone_else_does_not_overwrite_the_skin_account(
    ely_launcher: Launcher,
    server_state: ServerState,
) -> None:
    account = Account("Other", "069a79f4-44e9-4726-a5be-fca90e38aaf5", ELY)
    save_accounts(ely_launcher.paths.accounts_json, (account,))
    with pytest.raises(AccountError, match="selected for this skin"):
        ely_launcher.renew_ely_web_session(account.account_id, "jun@example.com", "secret")
    assert ely_launcher.list_accounts() == (account,)
    assert server_state.request_count("/elyweb/api/authentication/login") == 0


@pytest.mark.parametrize("failure", ["http", "oauth", "no-refresh-token"])
def test_web_failure_is_not_reported_as_success_and_preserves_existing_session(
    ely_launcher: Launcher,
    server_state: ServerState,
    failure: str,
) -> None:
    account = replace(old_account(ely_launcher), refresh_token="existing-web-ticket")
    save_accounts(ely_launcher.paths.accounts_json, (account,))
    if failure == "http":
        server_state.add("/elyweb/api/authentication/login", b"unavailable", status=500)
    elif failure == "oauth":
        server_state.add("/elyweb/api/oauth2/v1/complete", b'{"success":false}', status=400)
    else:
        server_state.add(
            "/elyweb/api/authentication/login", b'{"success":true,"access_token":"jwt"}'
        )
    with pytest.raises(AccountError):
        ely_launcher.renew_ely_web_session(account.account_id, "jun@example.com", "secret")
    assert ely_launcher.list_accounts() == (account,)


def test_two_factor_retry_keeps_the_account_until_web_authentication_succeeds(
    ely_launcher: Launcher,
    server_state: ServerState,
) -> None:
    account = old_account(ely_launcher)
    server_state.add(
        "/elyweb/api/authentication/login", b'{"success":false,"errors":{"totp":"required"}}'
    )
    with pytest.raises(TwoFactorRequired):
        ely_launcher.renew_ely_web_session(account.account_id, "jun@example.com", "secret")
    assert ely_launcher.list_accounts() == (account,)
    server_state.add(
        "/elyweb/api/authentication/login",
        json.dumps(
            {
                "success": True,
                "access_token": fake_ely.WEB_JWT,
                "refresh_token": fake_ely.WEB_REFRESH_TOKEN,
            }
        ).encode(),
    )
    ely_launcher.renew_ely_web_session(
        account.account_id, "jun@example.com", "secret", totp_code="123456"
    )
    assert b"totp=123456" in server_state.received_body("/elyweb/api/authentication/login")
    assert ely_launcher.list_accounts()[0].refresh_token == fake_ely.WEB_REFRESH_TOKEN


def test_initial_game_login_preserves_previous_web_ticket_during_web_outage(
    ely_launcher: Launcher,
    server_state: ServerState,
) -> None:
    account = replace(old_account(ely_launcher), refresh_token="existing-web-ticket")
    save_accounts(ely_launcher.paths.accounts_json, (account,))
    server_state.add("/elyweb/api/authentication/login", b"unavailable", status=500)
    renewed = ely_launcher.add_ely_account("jun@example.com", "secret")
    assert renewed.refresh_token == account.refresh_token
    assert renewed.access_token == fake_ely.ACCESS_TOKEN


def test_missing_account_is_rejected_before_any_network_request(
    ely_launcher: Launcher,
    server_state: ServerState,
) -> None:
    with pytest.raises(AccountError, match=r"existing Ely\.by account"):
        ely_launcher.renew_ely_web_session("ely:missing", "jun@example.com", "secret")
    assert server_state.request_count("/ely/auth/authenticate") == 0
