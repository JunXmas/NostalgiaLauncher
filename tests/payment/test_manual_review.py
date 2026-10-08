"""Yêu cầu duyệt Vietcombank vẫn chờ máy chủ; không tự cấp quyền ở launcher."""

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


def test_submit_only_reports_transfer_and_fetches_unchanged_pending_order(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient
) -> None:
    document = order_document()
    document.update(manual_review=True, submitted=False, checkout_url="")
    order = parse_order(document, parse_offer(offer_document()))
    path = "/v1/plus/orders/order_123/submit"
    server_state.add(path, b'{"submitted":true,"status":"pending"}')
    document["submitted"] = True
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    gateway = HttpPaymentGateway(server.url(""), "support-session", http_client)
    result = gateway.submit_transfer(order)
    assert result.status == "pending" and result.submitted and result.active_until == 0
    assert json.loads(server_state.received_body(path)) == {}
    with pytest.raises(PaymentError):
        gateway.fetch_order(replace(result, manual_review=False))
    document["submitted"] = False
    server_state.add("/v1/plus/orders/order_123", json.dumps(document).encode())
    with pytest.raises(PaymentError):
        gateway.fetch_order(result)


@pytest.mark.parametrize("response", [b'{"submitted":true,"status":"paid"}', b"{}"])
def test_submission_response_is_not_a_paid_receipt(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, response: bytes
) -> None:
    document = order_document()
    document["manual_review"] = True
    order = parse_order(document, parse_offer(offer_document()))
    server_state.add("/v1/plus/orders/order_123/submit", response)
    with pytest.raises(PaymentError):
        HttpPaymentGateway(server.url(""), "support-session", http_client).submit_transfer(order)


@pytest.mark.parametrize(
    ("field", "value"), [("manual_review", "true"), ("submitted", "true"), ("submitted", True)]
)
def test_manual_review_flags_must_be_explicit_booleans(field: str, value: JsonValue) -> None:
    document = order_document()
    document[field] = value
    with pytest.raises(PaymentError):
        parse_order(document, parse_offer(offer_document()))
