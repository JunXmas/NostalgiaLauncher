"""Ely.by: đăng nhập lưu vé (không lưu mật khẩu), 2FA thành lỗi riêng, làm mới trước khi chạy,
và authlib-injector được tải, kiểm sha256, cache, tiêm vào cờ JVM."""

from __future__ import annotations

import base64
import json
from dataclasses import replace
from pathlib import Path

import pytest

import fake_ely
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import ELY, to_player_profile
from nostalgia.errors import AuthError, IntegrityError, TwoFactorRequired
from test_api import make_launcher


def make_ely_launcher(server, server_state, tmp_path, certificate_pair):
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    return replace(launcher, auth_endpoints=fake_ely.publish(server, server_state))


def test_sign_in_keeps_tokens_but_never_the_password(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_ely_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "mat-khau-bi-mat", totp_code="123456")

    sent = json.loads(server_state.received_body("/ely/auth/authenticate"))
    assert sent["username"] == "jun@example.com" and sent["password"] == "mat-khau-bi-mat:123456"
    assert (account.player_name, account.player_uuid, account.account_kind) == (
        fake_ely.ELY_NAME,
        fake_ely.ELY_UUID,
        ELY,
    )
    assert account.access_token == fake_ely.ACCESS_TOKEN and account.client_token
    stored = launcher.paths.accounts_json.read_text()
    assert "mat-khau" not in stored and account.client_token in stored
    assert to_player_profile(account).user_type == "mojang"
    assert "mat-khau" not in repr(account)


def test_two_factor_and_bad_password_are_distinct_errors(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_ely_launcher(server, server_state, tmp_path, certificate_pair)
    route = server_state.routes["/ely/auth/authenticate"]
    route.status = 401
    route.body = (
        b'{"error":"ForbiddenOperationException",'
        b'"errorMessage":"Account protected with two factor auth."}'
    )
    with pytest.raises(TwoFactorRequired):
        launcher.add_ely_account("jun@example.com", "x")
    route.body = (
        b'{"error":"ForbiddenOperationException",'
        b'"errorMessage":"Invalid credentials. Invalid email or password."}'
    )
    with pytest.raises(AuthError, match="sai email"):
        launcher.add_ely_account("jun@example.com", "x")
    assert launcher.list_accounts() == ()


def test_launch_refreshes_the_ticket_and_injects_authlib(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_ely_launcher(server, server_state, tmp_path, certificate_pair)
    account = launcher.add_ely_account("jun@example.com", "x")

    refreshed = launcher._require_account(account.player_name, "", None)
    assert refreshed.access_token == fake_ely.REFRESHED_TOKEN
    assert json.loads(server_state.received_body("/ely/auth/refresh"))["clientToken"] == (
        account.client_token
    )

    arguments = launcher._authlib_arguments(refreshed)
    jar_path = launcher.paths.data_dir / "authlib-injector" / "authlib-injector-9.9.9.jar"
    assert jar_path.read_bytes() == fake_ely.INJECTOR_JAR
    assert arguments[0] == f"-javaagent:{jar_path}={launcher.auth_endpoints.ely_authlib_root_url}"
    assert base64.b64decode(arguments[1].split("=", 1)[1]) == fake_ely.API_METADATA

    server_state.routes["/authlib/latest.json"].status = 503  # mất mạng: dùng jar đã có
    assert launcher._authlib_arguments(refreshed)[0].startswith(f"-javaagent:{jar_path}")
    assert launcher._authlib_arguments(replace(account, account_kind="offline")) == ()


def test_tampered_injector_is_refused(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_ely_launcher(server, server_state, tmp_path, certificate_pair)
    server_state.routes["/authlib/authlib-injector-9.9.9.jar"].body = b"PK ma doc"
    account = launcher.add_ely_account("jun@example.com", "x")
    with pytest.raises(IntegrityError, match="sha256"):
        launcher._authlib_arguments(account)
    assert not list((launcher.paths.data_dir / "authlib-injector").glob("*.jar"))
