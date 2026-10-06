"""HTTPS thật: không gửi giá tự đặt, không tin xác nhận sai hoặc địa chỉ giả."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import PaymentError
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import HttpClient
from nostalgia.payment.gateway import HttpPaymentGateway
from nostalgia.payment.parse import parse_offer, parse_order
from payment_fixture import offer_document, order_document


def test_checkout_and_confirmation_over_https(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    document = order_document()
    server_state.add("/v1/plus/offer", json.dumps(offer_document()).encode())
    server_state.add("/v1/plus/orders", json.dumps(document).encode())
    gateway = HttpPaymentGateway(server.url(""), "support-session", http_client)
    offer = gateway.fetch_offer()
    order = gateway.create_order(offer, "request_123")
    assert order.status == "pending"
    assert json.loads(server_state.received_body("/v1/plus/orders")) == {"offer_id": "intro-year"}
    assert server_state.received_header("/v1/plus/orders", "Idempotency-Key") == "request_123"
    assert (
        server_state.received_header("/v1/plus/orders", "Authorization") == "Bearer support-session"
    )
    document.update(status="paid", active_until=order.expires_at + 365 * 86400)
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    assert gateway.fetch_order(order).status == "paid"


@pytest.mark.parametrize("status", [401, 403, 429, 500, 302])
def test_http_errors_do_not_become_a_confirmation(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    status: int,
) -> None:
    server_state.add("/v1/plus/orders", json.dumps(order_document("paid")).encode(), status=status)
    gateway = HttpPaymentGateway(server.url(""), "session", http_client)
    with pytest.raises(PaymentError):
        gateway.create_order(parse_offer(offer_document()), "request_123")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("amount", 1),
        ("amount", True),
        ("currency", "USD"),
        ("offer_id", "another-offer"),
        ("status", "success"),
        ("status", True),
        ("order_id", "../admin"),
        ("qr_image", "https://example.invalid/qr.png"),
        ("qr_image", "data:image/png;base64,aW52YWxpZA=="),
        ("account_number", "\uff11\uff12\uff13\uff14\uff15\uff16"),
        ("checkout_url", "https://pay.payos.vn.evil.example/"),
        ("checkout_url", "javascript:alert(1)"),
    ],
)
def test_malformed_order_is_rejected(field: str, value: JsonValue) -> None:
    document = order_document()
    document[field] = value
    with pytest.raises(PaymentError):
        parse_order(document, parse_offer(offer_document()))


def test_paid_requires_recorded_entitlement() -> None:
    document = order_document("paid")
    document["active_until"] = 0
    with pytest.raises(PaymentError):
        parse_order(document, parse_offer(offer_document()))


@pytest.mark.parametrize(
    ("field", "value"),
    [("order_id", "other"), ("expires_at", 1), ("holder", "OTHER"), ("transfer_memo", "OTHER")],
)
def test_polling_rejects_a_different_or_changed_order(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    field: str,
    value: JsonValue,
) -> None:
    document = order_document()
    order = parse_order(document, parse_offer(offer_document()))
    document[field] = value
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    with pytest.raises(PaymentError):
        HttpPaymentGateway(server.url(""), "session", http_client).fetch_order(order)


def test_confirmation_cannot_regress_to_pending(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    document = order_document()
    order = parse_order(document, parse_offer(offer_document()))
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    with pytest.raises(PaymentError):
        HttpPaymentGateway(server.url(""), "session", http_client).fetch_order(
            replace(order, status="paid", active_until=order.expires_at + 1)
        )


@pytest.mark.parametrize("url", ["http://localhost", "https://a:b@host", "https://host?key=secret"])
def test_insecure_service_config_is_rejected(http_client: HttpClient, url: str) -> None:
    with pytest.raises(PaymentError):
        HttpPaymentGateway(url, "session", http_client)
