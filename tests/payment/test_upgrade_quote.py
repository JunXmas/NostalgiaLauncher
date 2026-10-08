"""Giá báo theo tài khoản, đơn giữ nguyên giá và không tin nâng cấp 0đ chưa xác nhận."""

import json

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import PaymentError
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import HttpClient
from nostalgia.payment.gateway import HttpPaymentGateway
from nostalgia.payment.parse import parse_offer, parse_order
from payment_fixture import offer_document, order_document


def quoted_offer() -> dict[str, JsonValue]:
    return {
        **offer_document(),
        "amount": 40_000,
        "regular_amount": 69_000,
        "upgrade": True,
        "upgrade_credit": 29_000,
        "quote_id": "quote_123",
        "eligible": True,
        "current_plan": "plus-month-v1",
    }


def test_quote_identifier_is_sent_without_client_selected_price(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    document = order_document()
    document["amount"] = 40_000
    server_state.add("/v1/plus/orders", json.dumps(document).encode())
    gateway = HttpPaymentGateway(server.url(""), "session", http_client)
    assert gateway.create_order(parse_offer(quoted_offer()), "request_123").amount == 40_000
    assert json.loads(server_state.received_body("/v1/plus/orders")) == {
        "offer_id": "intro-year",
        "quote_id": "quote_123",
    }


def test_pending_invoice_price_does_not_change_when_prorated_credit_changes(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    document = {**order_document(), "amount": 40_000, "offer": quoted_offer()}
    server_state.add("/v1/plus/orders/current", json.dumps(document).encode())
    gateway = HttpPaymentGateway(server.url(""), "session", http_client)
    current_quote = {**quoted_offer(), "amount": 41_000, "upgrade_credit": 28_000}
    order = gateway.fetch_current_order(parse_offer(current_quote))
    assert order and order.amount == 40_000 and order.payment_offer
    document.update(status="paid", active_until=order.expires_at + 86400)
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    assert gateway.fetch_order(order).amount == 40_000


@pytest.mark.parametrize("bad_credit", [True, "29000", -1, 69_001])
def test_malformed_upgrade_credit_is_rejected(bad_credit: JsonValue) -> None:
    with pytest.raises(PaymentError):
        parse_offer({**quoted_offer(), "upgrade_credit": bad_credit})


def test_fully_funded_upgrade_requires_paid_order_and_integer_zero() -> None:
    document = {**quoted_offer(), "amount": 0, "upgrade_credit": 69_000}
    offer = parse_offer(document)
    with pytest.raises(PaymentError):
        parse_offer({**document, "amount": False})
    with pytest.raises(PaymentError):
        parse_order({**order_document(), "amount": 0}, offer)
    assert parse_order({**order_document("paid"), "amount": 0}, offer).status == "paid"
