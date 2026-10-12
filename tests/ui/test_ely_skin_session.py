"""Bấm Lưu ở tài khoản cũ mở đăng nhập tại chỗ, giữ preview và chỉ ghi skin sau xác nhận."""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from test_appearance_editor import account_page, png
from test_bridges import wait_until
from test_minimal_preview import Preview, find_control, press
from test_minimal_preview import preview as preview

from nostalgia.account.model import Account
from nostalgia.account.store import save_accounts
from nostalgia.api import Launcher
from nostalgia.errors import AccountError, TwoFactorRequired

pytestmark = pytest.mark.usefixtures("qt_app")


def test_missing_session_opens_sign_in_keeps_preview_and_allows_save_after_two_factor(
    preview: Preview,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher, view, bridge, root_item = preview
    account = replace(account_page(preview, monkeypatch, "ely"), refresh_token="")
    save_accounts(launcher.paths.accounts_json, (account,))
    bridge.announce_accounts_changed()
    account_bridge = view.rootContext().contextProperty("accountBridge")
    editor = view.rootContext().contextProperty("skinEditor")
    wait_until(lambda: not account_bridge.accountWithId(account.account_id)["elyWebReady"])
    path = png(tmp_path / "skin.png", "#7858c8")
    editor.importSkin(QUrl.fromLocalFile(str(path)).toString())
    wait_until(lambda: not editor.busy and editor.details["skinDirty"])
    original = editor.details["source"]
    saves = []
    logins = []

    def renew(
        self: Launcher, account_id: str, email_or_name: str, password: str, *, totp_code: str = ""
    ) -> Account:
        assert password == "private-password"
        logins.append((account_id, email_or_name, totp_code))
        if not totp_code:
            raise TwoFactorRequired("2FA required")
        renewed = replace(account, refresh_token="renewed-web-ticket")
        save_accounts(self.paths.accounts_json, (renewed,))
        return renewed

    monkeypatch.setattr(Launcher, "renew_ely_web_session", renew)
    monkeypatch.setattr(Launcher, "prefetch_skin_support", lambda _self: None)
    monkeypatch.setattr(
        Launcher,
        "save_skin_selection",
        lambda _self, selected, path, **_kw: saves.append(
            (selected.refresh_token, path.read_bytes())
        ),
    )
    press(view, find_control(root_item, "skinSaveButton"))
    dialog = find_control(root_item, "addAccountDialog")
    assert dialog.property("visible") and dialog.property("renewAccountId") == account.account_id
    assert not saves and editor.details["source"] == original and editor.details["dirty"]
    assert find_control(root_item, "elyEmailField").property("text") == account.player_name
    password_field = find_control(root_item, "elyPasswordField")
    password_field.setProperty("text", "private-password")
    press(view, find_control(root_item, "elySignInButton"))
    wait_until(lambda: bool(dialog.property("needsTotp")) and not account_bridge.busy)
    assert dialog.property("visible") and editor.details["source"] == original
    find_control(root_item, "elyTotpField").setProperty("text", "123456")
    press(view, find_control(root_item, "elySignInButton"))
    wait_until(lambda: not dialog.property("visible") and not account_bridge.busy)
    wait_until(lambda: account_bridge.accountWithId(account.account_id)["elyWebReady"])
    assert password_field.property("text") == ""
    assert find_control(root_item, "elyTotpField").property("text") == ""
    assert editor.details["source"] == original and editor.details["skinDirty"] and not saves
    assert logins == [
        (account.account_id, account.player_name, ""),
        (account.account_id, account.player_name, "123456"),
    ]
    save_button = find_control(root_item, "skinSaveButton")
    wait_until(lambda: bool(save_button.property("clickable")))
    press(view, save_button)
    wait_until(lambda: not editor.busy and not editor.details["dirty"])
    assert saves == [("renewed-web-ticket", path.read_bytes())]


def test_failed_or_cancelled_reauthentication_keeps_preview_and_clears_password(
    preview: Preview,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _launcher, view, _bridge, root_item = preview
    account_page(preview, monkeypatch, "ely")
    editor = view.rootContext().contextProperty("skinEditor")
    editor.importSkin(QUrl.fromLocalFile(str(png(tmp_path / "skin.png", "#38b786"))).toString())
    wait_until(lambda: not editor.busy and editor.details["dirty"])
    original = editor.details["source"]

    def fail(*_args: object, **_kwargs: object) -> None:
        raise AccountError("Web sign-in unavailable")

    monkeypatch.setattr(Launcher, "renew_ely_web_session", fail)
    press(view, find_control(root_item, "elySkinSignInButton"))
    dialog = find_control(root_item, "addAccountDialog")
    password_field = find_control(root_item, "elyPasswordField")
    password_field.setProperty("text", "private-password")
    press(view, find_control(root_item, "elySignInButton"))
    account_bridge = view.rootContext().contextProperty("accountBridge")
    wait_until(
        lambda: dialog.property("failure") == "Web sign-in unavailable" and not account_bridge.busy
    )
    assert dialog.property("visible") and editor.details["dirty"]
    press(view, find_control(root_item, "elySignInBackButton"))
    assert not dialog.property("visible") and password_field.property("text") == ""
    assert editor.details["source"] == original and editor.details["dirty"]
