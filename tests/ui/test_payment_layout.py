"""QR và thông tin phải nằm trong thẻ kể cả sau tải ảnh hoặc đổi cỡ chữ."""

from __future__ import annotations

import base64
import json
import time
from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QObject, QPointF
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import find_control, press
from test_payment_ui import PaymentPreview, create_order
from test_payment_ui import payment_preview as payment_preview  # fixture dùng chung

from nostalgia.auth.qr import encode_qr, qr_png_bytes

pytestmark = pytest.mark.usefixtures("qt_app")


def assert_within(control: Any, container: Any) -> None:
    origin = control.mapToItem(container, QPointF())
    assert origin.x() >= -0.5
    assert origin.y() >= -0.5
    assert origin.x() + control.width() <= container.width() + 0.5
    assert origin.y() + control.height() <= container.height() + 0.5


@pytest.mark.parametrize("scale", [100, 150])
def test_qr_and_transfer_fields_fit_the_card_after_resize(
    payment_preview: PaymentPreview, scale: int
) -> None:
    preview = payment_preview
    document = json.loads(preview.server_state.routes["/v1/plus/orders"].body)
    png = qr_png_bytes(encode_qr("X" * 120), scale=5)
    document["qr_image"] = "data:image/png;base64," + base64.b64encode(png).decode()
    preview.server_state.add("/v1/plus/orders", json.dumps(document).encode())
    create_order(preview)
    for width, height in [(1440, 900), (1024, 600)]:
        preview.view.resize(width, height)
        settings = preview.view.rootContext().contextProperty("settingsBridge")
        settings.setAppearance(scale, False, False, True, "vi")
        QTest.qWait(80)
        card = find_control(preview.root_item, "paymentQrCard")
        frame = find_control(preview.root_item, "paymentQrFrame")
        qr = find_control(preview.root_item, "paymentQr")
        assert_within(qr, frame)
        assert_within(frame, card)
        assert_within(qr, find_control(preview.root_item, "paymentScroll"))
        for field in ("amount", "accountNumber", "memo"):
            assert_within(
                find_control(preview.root_item, "paymentCopy-" + field).parentItem(), card
            )


@pytest.mark.parametrize("scale", [100, 150])
def test_receipt_has_no_upsell_and_keeps_main_action_visible(
    payment_preview: PaymentPreview, scale: int
) -> None:
    preview = payment_preview
    create_order(preview)
    document = json.loads(preview.server_state.routes["/v1/plus/orders"].body)
    document.update(status="paid", active_until=int(time.time()) + 365 * 86400)
    preview.server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    preview.payments.checkPayment()
    wait_until(lambda: preview.payments.details["stage"] == "paid")
    for width, height in [(1440, 900), (1024, 600)]:
        preview.view.resize(width, height)
        preview.view.rootContext().contextProperty("settingsBridge").setAppearance(
            scale, False, False, True, "vi"
        )
        QTest.qWait(80)
        assert preview.dialog.property("width") <= 760
        assert not preview.root_item.findChild(QObject, "paymentBenefits")
        card = find_control(preview.root_item, "paymentResultCard")
        order_row = find_control(preview.root_item, "paymentCopy-orderId").parentItem()
        assert_within(order_row, card)
        assert_within(order_row, find_control(preview.root_item, "paymentScroll"))
        done = find_control(preview.root_item, "paymentDone")
        assert done.isVisible()
        assert_within(done, preview.dialog.property("contentItem"))
    press(preview.view, done)
    assert not preview.dialog.property("opened")
