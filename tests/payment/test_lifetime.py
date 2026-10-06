"""Gói mua đứt phải được xác nhận riêng; 0 tháng không tự trở thành Plus vĩnh viễn."""

from __future__ import annotations

import json

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import PaymentError
from nostalgia.net.http import HttpClient
from nostalgia.payment.gateway import HttpPaymentGateway
from nostalgia.payment.parse import parse_offer, parse_order
from payment_fixture import offer_document, order_document


def test_lifetime_confirmation_over_https(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    document = offer_document()
    document.update(
        offer_id="plus-lifetime-v1",
        amount=209000,
        regular_amount=209000,
        duration_months=0,
        lifetime=True,
    )
    offer = parse_offer(document)
    document = order_document()
    document.update(offer_id=offer.offer_id, amount=offer.amount, lifetime=True)
    pending = parse_order(document, offer)
    document.update(status="paid", active_until=0)
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    paid = HttpPaymentGateway(server.url(""), "support-session", http_client).fetch_order(pending)
    assert paid.status == "paid" and paid.lifetime and paid.active_until == 0
    document["lifetime"] = False
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    with pytest.raises(PaymentError):
        HttpPaymentGateway(server.url(""), "support-session", http_client).fetch_order(pending)


@pytest.mark.parametrize("months,lifetime", [(0, False), (0, "true"), (12, True), (None, True)])
def test_ambiguous_lifetime_offer_is_rejected(months: object, lifetime: object) -> None:
    document = json.loads(json.dumps(offer_document()))
    document.update(duration_months=months, lifetime=lifetime)
    with pytest.raises(PaymentError):
        parse_offer(document)


def test_monthly_paid_order_cannot_gain_lifetime() -> None:
    document = order_document("paid")
    document.update(lifetime=True, active_until=0)
    with pytest.raises(PaymentError):
        parse_order(document, parse_offer(offer_document()))


@pytest.mark.parametrize("active_until", [None, True, "0", -1, 4200000000])
def test_lifetime_receipt_requires_explicit_zero(active_until: object) -> None:
    offer_fields = json.loads(json.dumps(offer_document()))
    offer_fields.update(duration_months=0, lifetime=True)
    document = json.loads(json.dumps(order_document("paid")))
    document.update(lifetime=True, active_until=active_until)
    with pytest.raises(PaymentError):
        parse_order(document, parse_offer(offer_fields))
