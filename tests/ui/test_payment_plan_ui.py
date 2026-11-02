"""Nostalgia+ có đúng hai lựa chọn dùng offer máy chủ; Worker còn bảng giá cũ vẫn bán được."""

from __future__ import annotations

import json

import pytest
import test_payment_ui
from test_bridges import wait_until
from test_main_window import find_control as find_object
from test_main_window import press
from test_payment_ui import PaymentPreview
from test_social_ui import find_control

from payment_fixture import offer_document, order_document

payment_preview = test_payment_ui.payment_preview
pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize(
    ("button", "amount", "offer_id", "lifetime"),
    [
        ("plusPlanYearly", 79_000, "plus-year-v3", False),
        ("plusPlanLifetime", 199_000, "plus-lifetime-v2", True),
    ],
)
def test_plan_clicks_price_and_pending_order_keeps_its_plan(
    payment_preview: PaymentPreview, button: str, amount: int, offer_id: str, lifetime: bool
) -> None:
    preview = payment_preview
    offer = offer_document()
    offer.update(
        offer_id=offer_id,
        amount=amount,
        regular_amount=amount,
        duration_months=0 if lifetime else 12,
        lifetime=lifetime,
    )
    preview.server_state.add("/v1/plus/offer", json.dumps(offer).encode())
    scroll = find_object(preview.root_item, "paymentScroll")
    press(preview.view, find_control(scroll, button))
    wait_until(lambda: not preview.payments.busy and preview.payments.details["available"])
    assert preview.server_state.received_path("/v1/plus/offer").endswith("offer_id=" + offer_id)
    assert preview.payments.details["amount"] == amount
    assert preview.payments.details["lifetime"] is lifetime
    order = order_document()
    order.update(offer_id=offer_id, amount=amount, lifetime=lifetime)
    preview.server_state.add("/v1/plus/orders", json.dumps(order).encode())
    press(preview.view, find_object(preview.root_item, "paymentCreate"))
    wait_until(lambda: preview.payments.details["stage"] == "pending" and not preview.payments.busy)
    preview.payments.selectPlan(not lifetime)
    assert preview.payments.details["amount"] == amount


def test_old_worker_rejecting_new_offer_falls_back_to_its_default_offer(
    payment_preview: PaymentPreview, caplog: pytest.LogCaptureFixture
) -> None:
    """Worker chưa deploy chỉ biết 4 gói cũ: launcher mới vẫn hiện giá máy chủ và tạo được đơn."""
    preview = payment_preview
    old_offer = offer_document()
    old_offer.update(offer_id="plus-year-v2", amount=109_000, regular_amount=109_000)
    preview.server_state.add("/v1/plus/offer", json.dumps(old_offer).encode(), fail_first=1)
    press(
        preview.view,
        find_control(find_object(preview.root_item, "paymentScroll"), "plusPlanYearly"),
    )
    wait_until(lambda: not preview.payments.busy and preview.payments.details["available"])
    assert preview.server_state.request_count("/v1/plus/offer") == 2
    assert preview.server_state.received_path("/v1/plus/offer") == "/v1/plus/offer"
    assert preview.payments.details["amount"] == 109_000 and not preview.payments.details["error"]
    assert any("plus-year-v3" in record.getMessage() for record in caplog.records)
    order = order_document()
    order.update(offer_id="plus-year-v2", amount=109_000)
    preview.server_state.add("/v1/plus/orders", json.dumps(order).encode())
    press(preview.view, find_object(preview.root_item, "paymentCreate"))
    wait_until(lambda: preview.payments.details["stage"] == "pending" and not preview.payments.busy)
    assert json.loads(preview.server_state.received_body("/v1/plus/orders")) == {
        "offer_id": "plus-year-v2"
    }
