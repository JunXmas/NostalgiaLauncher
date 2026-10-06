"""Tương tác Qt thật với dịch vụ HTTPS giả; bấm kiểm tra không tự mở khóa."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import find_control, press

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import HttpPaymentGateway, Launcher
from nostalgia.content.model import SearchPage
from nostalgia.net.http import HttpClient
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background
from payment_fixture import offer_document, order_document

pytestmark = pytest.mark.usefixtures("qt_app")


@dataclass(frozen=True, slots=True)
class PaymentPreview:
    view: Any
    root_item: Any
    payments: Any
    dialog: Any
    server_state: ServerState


@pytest.fixture
def payment_preview(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
) -> Iterator[PaymentPreview]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    launcher.add_offline_account("JunPreview")
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    server_state.add("/v1/plus/offer", json.dumps(offer_document()).encode())
    server_state.add("/v1/plus/orders", json.dumps(order_document()).encode())
    server_state.add("/v1/plus/orders/current", b"null")
    view, bridge = open_preview(
        launcher,
        payment_gateway=HttpPaymentGateway(server.url(""), "support-session", http_client),
    )
    root_item = view.rootObject()
    assert root_item is not None, [error.toString() for error in view.errors()]
    view.show()
    view.requestActivate()
    press(view, find_control(root_item, "openSupport"))
    payments = view.rootContext().contextProperty("paymentBridge")
    wait_until(lambda: payments.details["available"] and not payments.busy)
    wait_until(lambda: bool(find_control(root_item, "paymentCreate").property("clickable")))
    QTest.qWait(30)
    yield PaymentPreview(
        view, root_item, payments, find_control(root_item, "supportDialog"), server_state
    )
    bridge.cancelSignIn()
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def create_order(preview: PaymentPreview) -> None:
    wait_until(
        lambda: bool(find_control(preview.root_item, "paymentCreate").property("clickable"))
    )
    press(preview.view, find_control(preview.root_item, "paymentCreate"))
    wait_until(lambda: preview.payments.details["stage"] == "pending" and not preview.payments.busy)


def test_payment_button_only_checks_and_server_confirms(payment_preview: PaymentPreview) -> None:
    preview = payment_preview
    assert preview.dialog.property("modal")
    create_order(preview)
    press(preview.view, find_control(preview.root_item, "paymentCopy-memo"))
    assert QGuiApplication.clipboard().text() == "DEMO ORDER 123"
    before = preview.payments.details.copy()
    assert not preview.payments.setProperty("paid", True)
    assert preview.payments.details == before
    path = "/v1/plus/orders/order_123"
    document = json.loads(preview.server_state.routes["/v1/plus/orders"].body)
    preview.server_state.add(path, json.dumps(document).encode())
    press(preview.view, find_control(preview.root_item, "paymentCheck"))
    wait_until(lambda: preview.server_state.request_count(path) == 1 and not preview.payments.busy)
    assert preview.payments.details["stage"] == "pending"
    document.update(status="paid", active_until=int(time.time()) + 365 * 86400)
    preview.server_state.add(path, json.dumps(document).encode())
    preview.payments.checkPayment()
    wait_until(lambda: preview.payments.details["stage"] == "paid")
    assert not preview.payments._poll.isActive()


def test_close_and_reopen_preserves_order_and_stops_polling(
    payment_preview: PaymentPreview,
) -> None:
    preview = payment_preview
    create_order(preview)
    request_id = preview.server_state.received_header("/v1/plus/orders", "Idempotency-Key")
    preview.dialog.close()
    QTest.qWait(50)
    assert not preview.payments._poll.isActive()
    assert preview.payments.details["orderId"] == "order_123"
    preview.payments.createOrder()
    assert preview.server_state.request_count("/v1/plus/orders") == 1
    assert preview.server_state.received_header("/v1/plus/orders", "Idempotency-Key") == request_id
    preview.server_state.add(
        "/v1/plus/orders/order_123", preview.server_state.routes["/v1/plus/orders"].body
    )
    preview.dialog.open()
    wait_until(lambda: not preview.payments.busy)
    assert preview.payments.details["orderId"] == "order_123"


def test_network_error_keeps_order_and_allows_retry(payment_preview: PaymentPreview) -> None:
    preview = payment_preview
    create_order(preview)
    path = "/v1/plus/orders/order_123"
    preview.server_state.add(path, b"{}", status=500)
    preview.payments.checkPayment()
    wait_until(lambda: bool(preview.payments.details["error"]) and not preview.payments.busy)
    assert preview.payments.details["stage"] == "pending"
    assert preview.payments.details["qr"]
    preview.server_state.add(path, preview.server_state.routes["/v1/plus/orders"].body)
    preview.payments.checkPayment()
    wait_until(lambda: not preview.payments.busy and not preview.payments.details["error"])


def test_small_window_large_text_and_donation_are_accessible(
    payment_preview: PaymentPreview,
) -> None:
    preview = payment_preview
    preview.view.resize(1024, 600)
    settings = preview.view.rootContext().contextProperty("settingsBridge")
    settings.setAppearance(150, False, False, True, "vi")
    QTest.qWait(60)
    mica = find_control(preview.root_item, "paymentMica")
    origin = mica.mapToScene(QPointF())
    assert mica.property("backdropRect").x() == pytest.approx(origin.x())
    assert mica.property("backdropRect").y() == pytest.approx(origin.y())
    scroll = find_control(preview.root_item, "paymentScroll")
    assert scroll.property("contentHeight") > scroll.height()
    scroll.setProperty("contentY", scroll.property("contentHeight") - scroll.height())
    create_order(preview)
    qr = find_control(preview.root_item, "paymentQr")
    assert qr.width() == qr.implicitWidth()
    press(preview.view, find_control(preview.root_item, "paymentDonation"))
    assert find_control(preview.root_item, "donateDialog").property("visible")
    QTest.keyClick(preview.view, Qt.Key.Key_Escape)
