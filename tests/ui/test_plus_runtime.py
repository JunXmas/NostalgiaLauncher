"""Release checkout keeps pending orders, refreshes server rights, and clears them on logout."""

import json
import time
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtGui import QDesktopServices, QGuiApplication
from test_bridges import wait_until

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Launcher
from nostalgia.model.json_value import JsonValue, as_mapping
from nostalgia.net.http import HttpClient
from nostalgia.ui.runtime import build_release_view
from nostalgia.ui.worker import wait_for_background
from payment_fixture import offer_document, order_document


@pytest.mark.usefixtures("qt_app")
def test_release_manual_purchase_refreshes_rights_and_logout_revokes_gateways(
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
    monkeypatch.setenv("NOSTALGIA_ACCOUNT_URL", server.url(""))
    monkeypatch.setenv("NOSTALGIA_ROOM_SYNC_URL", server.url(""))
    monkeypatch.setattr(Launcher, "make_http_client", lambda _self: http_client)
    monkeypatch.setattr(Launcher, "make_service_session_store", lambda _self, _origin: None)
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda _url: True)
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
        "/v1/auth/google/poll", b'{"status":"signed_in","access_token":"' + b"a" * 64 + b'"}'
    )
    server_state.add("/v1/auth/encryption-key", b'{"registered":true}')
    server_state.add("/v1/auth/logout", b'{"signed_out":true}')
    snapshot: dict[str, JsonValue] = {
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
    server_state.add("/v1/me", json.dumps(snapshot).encode())
    offer = offer_document()
    offer.update(
        offer_id="plus-half-year-v1",
        amount=69000,
        regular_amount=69000,
        duration_months=6,
        lifetime=False,
    )
    server_state.add("/v1/plus/offer", json.dumps(offer).encode())
    server_state.add("/v1/plus/orders/current", b"null")
    purchase = order_document()
    purchase.update(
        offer_id="plus-half-year-v1",
        amount=69000,
        lifetime=False,
        manual_review=True,
        submitted=False,
        checkout_url="",
    )
    server_state.add("/v1/plus/orders", json.dumps(purchase).encode())
    server_state.add("/v1/plus/orders/order_123", json.dumps(purchase).encode())
    server_state.add("/v1/plus/orders/order_123/submit", b'{"status":"pending","submitted":true}')
    server_state.add(
        "/v1/servers/access",
        b'{"plan_name":"Pro","server_hosting":true,"hosting_mode":"local","maximum_running":1}',
    )
    view = build_release_view(launcher)
    social = view.rootContext().contextProperty("socialBridge")
    payments = view.rootContext().contextProperty("paymentBridge")
    repair = view.rootContext().contextProperty("modRepairBridge")
    servers = view.rootContext().contextProperty("serverBridge")
    synchronization = view.rootContext().contextProperty("roomSyncBridge")
    try:
        assert view.rootContext().contextProperty("plusFeaturesEnabled") is True
        assert not payments.details["available"]
        payments.setWatching(True)
        social._login_timer.setInterval(40)
        social.signIn()
        # Match the UI: an offer arriving does not yet mean its worker is idle.
        wait_until(
            lambda: (
                social.signedIn
                and not social.busy
                and payments.details["available"]
                and not payments.busy
            )
        )
        assert not social.account["plus"] and repair._gateway is None
        assert synchronization.configured
        payments.createOrder()
        wait_until(lambda: payments.details["stage"] == "pending" and not payments.busy)
        assert (
            server_state.received_header("/v1/plus/orders", "Authorization") == "Bearer " + "a" * 64
        )
        assert server_state.received_header("/v1/plus/orders", "Nostalgia-Proof")
        assert json.loads(server_state.received_body("/v1/plus/orders")) == {
            "offer_id": "plus-half-year-v1"
        }
        purchase["submitted"] = True
        server_state.add("/v1/plus/orders/order_123", json.dumps(purchase).encode())
        payments.submitTransfer()
        wait_until(lambda: payments.details["stage"] == "reviewing" and not payments.busy)
        social.refresh()
        wait_until(lambda: not social.busy)
        assert payments.details["orderId"] == "order_123"
        assert not social.account["plus"] and repair._gateway is None
        assert server_state.request_count("/v1/plus/orders") == 1
        paid_until = int(time.time()) + 180 * 86400
        purchase.update(status="paid", active_until=paid_until)
        server_state.add("/v1/plus/orders/order_123", json.dumps(purchase).encode())
        as_mapping(snapshot["account"]).update(plus_until=paid_until, plus_plan="plus-half-year-v1")
        server_state.add("/v1/me", json.dumps(snapshot).encode())
        payments.checkPayment()
        wait_until(lambda: social.account["plus"] and repair._gateway is not None)
        assert payments.details["stage"] == "paid"
        assert social.account["planName"] == "Pro"
        servers.checkAccess()
        wait_until(lambda: servers.hasAccess and not servers.busy)
        social.signOut()
        wait_until(lambda: not social.signedIn and not social.busy)
        assert payments.details["stage"] == "unavailable" and repair._gateway is None
        assert not servers.hasAccess and not synchronization.configured
        assert launcher.list_accounts()[0].player_name == "MinecraftLocal"
    finally:
        payments.setWatching(False)
        social.shutdown()
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
