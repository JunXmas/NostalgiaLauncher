"""Release login wires authenticated services; a free Google account stays free."""

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from test_bridges import wait_until

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Launcher, ServiceConfiguration
from nostalgia.net.http import HttpClient
from nostalgia.ui.runtime import build_release_view
from nostalgia.ui.worker import wait_for_background


@pytest.mark.usefixtures("qt_app")
def test_release_google_auto_poll_keeps_free_account_free(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    launcher.add_offline_account("MinecraftLocal")
    launcher.save_service_configuration(ServiceConfiguration(server.url("")))
    monkeypatch.setenv("NOSTALGIA_ACCOUNT_URL", server.url(""))
    monkeypatch.setenv("NOSTALGIA_ROOM_SYNC_URL", "")
    monkeypatch.setattr(Launcher, "make_http_client", lambda _self: http_client)
    monkeypatch.setattr(Launcher, "make_service_session_store", lambda _self, _origin: None)
    urls: list[str] = []

    def open_browser(url: QUrl) -> bool:
        urls.append(url.toString())
        return True

    monkeypatch.setattr(QDesktopServices, "openUrl", open_browser)
    server_state.add(
        "/v1/auth/google/start",
        json.dumps(
            {
                "login_id": "attempt",
                "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?state=fixture",
                "expires_at": int(time.time()) + 300,
            }
        ).encode(),
    )
    server_state.add(
        "/v1/auth/google/poll",
        b'{"status":"signed_in","access_token":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}',
    )
    server_state.add("/v1/auth/encryption-key", b'{"registered":true}')
    server_state.add(
        "/v1/me",
        json.dumps(
            {
                "account": {
                    "account_id": "owner",
                    "name": "GooglePlayer",
                    "friend_code": "ABCDEF0123456789",
                    "plus_until": 0,
                    "plus_lifetime": False,
                    "plus_plan": "",
                },
                "friends": [],
                "requests": [],
                "invitations": [],
            }
        ).encode(),
    )
    view = build_release_view(launcher)
    social = view.rootContext().contextProperty("socialBridge")
    try:
        social._login_timer.setInterval(40)
        social.signIn()
        wait_until(lambda: social.signedIn and not social.busy)
        assert len(urls) == 1 and urls[0].startswith("https://accounts.google.com/")
        assert social.account["name"] == "GooglePlayer"
        assert not social.account["plus"] and not social.account["profilePlus"]
        assert not social.account["cosmeticPlus"]
        assert not social.account["earlyPreview"]
        assert view.rootObject().findChild(QObject, "serviceAccountUrl") is None
        payment = view.rootContext().contextProperty("paymentBridge")
        payment.createOrder()
        assert payment.details["stage"] == "offer" and not payment.busy
        assert view.rootContext().contextProperty("plusFeaturesEnabled") is True
        assert not view.rootContext().contextProperty("modRepairBridge").details["canPlan"]
        assert launcher.list_accounts()[0].player_name == "MinecraftLocal"
    finally:
        social.shutdown()
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
