"""Bốn lựa chọn Plus dùng offer máy chủ; không đổi gói của đơn đang chờ."""

from __future__ import annotations

import json

import pytest
import test_payment_ui
from test_bridges import wait_until
from test_minimal_preview import find_control as find_object
from test_minimal_preview import press
from test_payment_ui import PaymentPreview
from test_social_ui import find_control

from payment_fixture import offer_document, order_document

payment_preview = test_payment_ui.payment_preview
pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize(
    ("months", "amount", "offer_id"),
    [
        (1, 29000, "plus-month-v1"),
        (6, 69000, "plus-half-year-v1"),
        (12, 109000, "plus-year-v2"),
        (0, 209000, "plus-lifetime-v1"),
    ],
)
def test_plan_clicks_price_and_receipt_duration(
    payment_preview: PaymentPreview, months: int, amount: int, offer_id: str
) -> None:
    preview = payment_preview
    offer = offer_document()
    offer.update(
        offer_id=offer_id,
        amount=amount,
        regular_amount=amount,
        duration_months=months,
        lifetime=months == 0,
    )
    preview.server_state.add("/v1/plus/offer", json.dumps(offer).encode())
    scroll = find_object(preview.root_item, "paymentScroll")
    press(preview.view, find_control(scroll, "plusPlan-" + str(months)))
    wait_until(lambda: not preview.payments.busy and preview.payments.details["available"])
    assert (
        preview.payments.details["months"] == months
        and preview.payments.details["amount"] == amount
    )
    order = order_document()
    order.update(offer_id=offer_id, amount=amount, lifetime=months == 0)
    preview.server_state.add("/v1/plus/orders", json.dumps(order).encode())
    press(preview.view, find_object(preview.root_item, "paymentCreate"))
    wait_until(lambda: preview.payments.details["stage"] == "pending" and not preview.payments.busy)
    preview.payments.selectPlan(6 if months == 12 else 12)
    assert (
        preview.payments.details["months"] == months
        and preview.payments.details["amount"] == amount
    )
