"""Bấm đã chuyển khoản trong Qt chỉ chuyển sang chờ duyệt, chưa mở khóa Plus."""

from __future__ import annotations

import json
import time

import pytest

pytest.importorskip("PySide6")
from test_bridges import wait_until
from test_minimal_preview import find_control, press
from test_payment_ui import PaymentPreview, create_order
from test_payment_ui import payment_preview as payment_preview

pytestmark = pytest.mark.usefixtures("qt_app")


def test_transfer_request_waits_for_review_even_after_qr_expires(
    payment_preview: PaymentPreview, monkeypatch: pytest.MonkeyPatch
) -> None:
    preview = payment_preview
    document = json.loads(preview.server_state.routes["/v1/plus/orders"].body)
    document.update(manual_review=True, submitted=False, checkout_url="")
    preview.server_state.add("/v1/plus/orders", json.dumps(document).encode())
    create_order(preview)
    document["submitted"] = True
    preview.server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    preview.server_state.add(
        "/v1/plus/orders/order_123/submit", b'{"submitted":true,"status":"pending"}'
    )
    press(preview.view, find_control(preview.root_item, "paymentSubmitTransfer"))
    wait_until(
        lambda: preview.payments.details["stage"] == "reviewing" and not preview.payments.busy
    )
    assert not preview.payments.details["activeUntil"]
    assert not preview.payments.details["qr"]
    assert preview.payments._poll.interval() == 30_000
    assert (
        find_control(preview.root_item, "paymentResultTitle").property("text")
        == "Chờ duyệt thanh toán"
    )
    monkeypatch.setattr(time, "time", lambda: document["expires_at"] + 1)
    assert preview.payments.details["stage"] == "reviewing"
    preview.payments.newOrder()
    assert preview.payments.details["orderId"] == "order_123"
