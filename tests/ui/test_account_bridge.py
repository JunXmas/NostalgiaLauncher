"""Cầu nối TÀI KHOẢN: mỗi tài khoản có file skin vẽ được ngay (mặc định Steve/Alex), đăng nhập
Ely.by qua bridge kích hoạt tài khoản mới, 2FA thành tín hiệu riêng, mật khẩu không nằm ở đâu."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until
from test_ely_upload import make_ely_web_launcher

import fake_ely
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.model import ELY, Account
from nostalgia.account.store import save_accounts
from nostalgia.api import Launcher
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
    web = fake_ely.publish_web(server, server_state)
    launcher = replace(
        launcher,
        auth_endpoints=replace(
            fake_ely.publish(server, server_state),
            ely_web_account_root=web.account_root,
            ely_web_site_root=web.site_root,
        ),
    )
    launcher.add_offline_account("Dinnerbone")
    main_bridge = LauncherBridge(launcher)
    account_bridge = AccountBridge(launcher, main_bridge)

    rows = account_bridge.accounts
    assert len(rows) == 1 and rows[0]["kindLabel"] == "NGOẠI TUYẾN"
    assert rows[0]["skinFile"].startswith("file://") and rows[0]["skinFile"].endswith(".png")
    assert rows[0]["isDefaultSkin"] is True and rows[0]["capeFile"] == ""
    assert account_bridge.accountWithId(rows[0]["accountId"])["playerName"] == "Dinnerbone"
    assert account_bridge.accountWithId("ai-do") == {}

    signed: list[str] = []
    account_bridge.elySignedIn.connect(signed.append)
    account_bridge.signInEly(" jun@example.com ", "mat-khau", "")
    wait_until(lambda: bool(signed) and not account_bridge.busy)
    assert signed == [fake_ely.ELY_NAME]
    assert main_bridge.activePlayerName == fake_ely.ELY_NAME
    ely_row = next(
        account for account in account_bridge.accounts if account["accountKind"] == "ely"
    )
    assert account_bridge.accountWithId(ely_row["accountId"])["kindLabel"] == "ELY.BY"
    assert "mat-khau" not in launcher.paths.accounts_json.read_text()
    assert ely_row["elyWebReady"] is True
    assert not {"access_token", "refresh_token", "site_cookies", "jwt"} & ely_row.keys()


def test_two_factor_is_a_signal_not_a_failure(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    web = fake_ely.publish_web(server, server_state)
    launcher = replace(
        launcher,
        auth_endpoints=replace(
            fake_ely.publish(server, server_state),
            ely_web_account_root=web.account_root,
            ely_web_site_root=web.site_root,
        ),
    )
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


def test_ely_sign_in_fetches_skin_support_right_away(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Tải authlib-injector ngay sau khi đăng nhập, không đợi tới lúc bấm CHƠI: lúc này người
    dùng vừa nhập mật khẩu nên chắc chắn có mạng và đang chờ sẵn, còn một lỗi mạng ở nút CHƠI
    thì đọc ra "launcher hỏng"."""
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    web = fake_ely.publish_web(server, server_state)
    launcher = replace(
        launcher,
        auth_endpoints=replace(
            fake_ely.publish(server, server_state),
            ely_web_account_root=web.account_root,
            ely_web_site_root=web.site_root,
        ),
    )
    main_bridge = LauncherBridge(launcher)
    account_bridge = AccountBridge(launcher, main_bridge)
    assert account_bridge.skinSupportReady is False

    signed: list[str] = []
    account_bridge.elySignedIn.connect(signed.append)
    account_bridge.signInEly("jun@example.com", "x", "")
    wait_until(lambda: bool(signed) and not account_bridge.busy)

    wait_until(lambda: account_bridge.skinSupportReady)
    assert account_bridge.skinSupportReady is True


def test_targeted_web_sign_in_updates_session_without_switching_the_active_account(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = make_ely_web_launcher(server, server_state, tmp_path, certificate_pair)
    account = Account(fake_ely.ELY_NAME, fake_ely.ELY_UUID, ELY)
    save_accounts(launcher.paths.accounts_json, (account,))
    other = launcher.add_offline_account("StillSelected")
    monkeypatch.setattr(
        Launcher, "refresh_skin", lambda self, selected: self.describe_skin(selected)
    )
    main_bridge = LauncherBridge(launcher)
    main_bridge.setActiveAccount(other.account_id)
    account_bridge = AccountBridge(launcher, main_bridge)
    assert not account_bridge.accountWithId(account.account_id)["elyWebReady"]
    signed: list[str] = []
    account_bridge.elySignedIn.connect(signed.append)
    account_bridge.signInEly("jun@example.com", "secret", "", account.account_id)
    wait_until(lambda: bool(signed) and not account_bridge.busy)
    assert main_bridge.activeAccountId == other.account_id
    assert account_bridge.accountWithId(account.account_id)["elyWebReady"]
    assert len(launcher.list_accounts()) == 2
