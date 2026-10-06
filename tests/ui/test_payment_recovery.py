"""Đơn thất bại, hết giờ ở máy khách và chưa có backend phải giữ trạng thái an toàn."""

from __future__ import annotations

import json
import time

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QGuiApplication
from test_bridges import wait_until
from test_minimal_preview import find_control, press
from test_payment_ui import PaymentPreview, create_order
from test_payment_ui import payment_preview as payment_preview  # fixture dùng chung của pytest

from nostalgia.ui.payment_bridge import PaymentBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_unconfigured_payment_does_not_create_or_confirm() -> None:
    payments = PaymentBridge()
    payments.setWatching(True)
    payments.createOrder()
    payments.checkPayment()
    assert payments.details["stage"] == "unavailable"
    assert not payments.details["available"]
    assert not payments.details["qr"]
    assert not payments.details["activeUntil"]
    payments.setWatching(False)
    payments.deleteLater()
    QGuiApplication.processEvents()


def test_failed_creation_reuses_idempotency_key(payment_preview: PaymentPreview) -> None:
    preview = payment_preview
    route = preview.server_state.routes["/v1/plus/orders"]
    document = route.body
    preview.server_state.add("/v1/plus/orders", b"{}", status=500)
    press(preview.view, find_control(preview.root_item, "paymentCreate"))
    wait_until(lambda: bool(preview.payments.details["error"]) and not preview.payments.busy)
    request_id = preview.server_state.received_header("/v1/plus/orders", "Idempotency-Key")
    assert preview.payments.details["stage"] == "offer"
    preview.server_state.add("/v1/plus/orders", document)
    create_order(preview)
    assert preview.server_state.received_header("/v1/plus/orders", "Idempotency-Key") == request_id


def test_clock_expiry_hides_qr_and_waits_for_server(
    payment_preview: PaymentPreview, monkeypatch: pytest.MonkeyPatch
) -> None:
    preview = payment_preview
    create_order(preview)
    clock = time.time() + 1800
    monkeypatch.setattr(time, "time", lambda: clock)
    assert preview.payments.details["stage"] == "verifying"
    assert not preview.payments.details["qr"]
    preview.payments.newOrder()
    assert preview.payments.details["orderId"] == "order_123"
    document = json.loads(preview.server_state.routes["/v1/plus/orders"].body)
    document["status"] = "expired"
    preview.server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    preview.payments.checkPayment()
    wait_until(lambda: preview.payments.details["stage"] == "expired" and not preview.payments.busy)
    preview.payments.newOrder()
    wait_until(lambda: preview.payments.details["stage"] == "offer" and not preview.payments.busy)


def test_new_window_resumes_server_order(payment_preview: PaymentPreview) -> None:
    preview = payment_preview
    create_order(preview)
    preview.server_state.add(
        "/v1/plus/orders/current", preview.server_state.routes["/v1/plus/orders"].body
    )
    returning = PaymentBridge(preview.payments._gateway)
    returning.setWatching(True)
    wait_until(lambda: returning.details["stage"] == "pending" and not returning.busy)
    assert returning.details["orderId"] == "order_123"
    returning.createOrder()
    assert preview.server_state.request_count("/v1/plus/orders") == 1
    returning.setWatching(False)
    returning.deleteLater()
    QGuiApplication.processEvents()


def test_terminal_server_order_allows_a_new_checkout(payment_preview: PaymentPreview) -> None:
    preview = payment_preview
    document = json.loads(preview.server_state.routes["/v1/plus/orders"].body)
    document["status"] = "expired"
    preview.server_state.add("/v1/plus/orders/current", json.dumps(document).encode())
    payments = PaymentBridge(preview.payments._gateway)
    payments.setWatching(True)
    wait_until(lambda: payments.details["available"] and not payments.busy)
    assert payments.details["stage"] == "offer"
    assert not payments.details["orderId"]
    payments.setWatching(False)
    payments.deleteLater()
    QGuiApplication.processEvents()
