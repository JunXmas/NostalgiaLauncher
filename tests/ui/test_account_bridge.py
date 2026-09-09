"""Cầu nối TÀI KHOẢN: mỗi tài khoản có file skin vẽ được ngay (mặc định Steve/Alex), đăng nhập
Ely.by qua bridge kích hoạt tài khoản mới, 2FA thành tín hiệu riêng, mật khẩu không nằm ở đâu."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until

import fake_ely
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.bridge import LauncherBridge
from test_api import make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")


def test_accounts_carry_a_drawable_skin_and_ely_sign_in_activates(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(launcher, auth_endpoints=fake_ely.publish(server, server_state))
    launcher.add_offline_account("Dinnerbone")
    main_bridge = LauncherBridge(launcher)
    account_bridge = AccountBridge(launcher, main_bridge)

    rows = account_bridge.accounts
    assert len(rows) == 1 and rows[0]["kindLabel"] == "NGOẠI TUYẾN"
    assert rows[0]["skinFile"].startswith("file://") and rows[0]["skinFile"].endswith(".png")
    assert rows[0]["isDefaultSkin"] is True and rows[0]["capeFile"] == ""
    assert account_bridge.accountNamed("Dinnerbone")["playerName"] == "Dinnerbone"
    assert account_bridge.accountNamed("ai-do") == {}

    signed: list[str] = []
    account_bridge.elySignedIn.connect(signed.append)
    account_bridge.signInEly(" jun@example.com ", "mat-khau", "")
    wait_until(lambda: bool(signed) and not account_bridge.busy)
    assert signed == [fake_ely.ELY_NAME]
    assert main_bridge.activePlayerName == fake_ely.ELY_NAME
    assert account_bridge.accountNamed(fake_ely.ELY_NAME)["kindLabel"] == "ELY.BY"
    assert "mat-khau" not in launcher.paths.accounts_json.read_text()


def test_two_factor_is_a_signal_not_a_failure(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(launcher, auth_endpoints=fake_ely.publish(server, server_state))
    route = server_state.routes["/ely/auth/authenticate"]
    route.status = 401
    route.body = b'{"errorMessage":"Account protected with two factor auth."}'
    main_bridge = LauncherBridge(launcher)
    account_bridge = AccountBridge(launcher, main_bridge)
    events: list[str] = []
    account_bridge.twoFactorRequired.connect(lambda: events.append("2fa"))
    account_bridge.failed.connect(events.append)

    account_bridge.signInEly("jun@example.com", "x", "")
    wait_until(lambda: bool(events) and not account_bridge.busy)
    assert events == ["2fa"] and launcher.list_accounts() == ()
