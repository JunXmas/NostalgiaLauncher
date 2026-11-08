"""Transport cô lập: public catalog không mang phiên, mọi thay đổi ví phải có proof."""

import json
from typing import Any, cast

import pytest

from nostalgia.errors import SessionRevoked
from nostalgia.marketplace.gateway import HttpMarketGateway
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.net.session_proof import forget_session, register_session


class MarketTransport:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, bytes | None, dict[str, str]]] = []

    def send(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
        self.calls.append((method, url, kwargs.get("body"), kwargs["headers"]))
        if url.endswith("/catalog"):
            payload = {"schema_version": 1, "enabled": False, "products": [], "coin_offers": []}
        elif url.endswith("/quotes"):
            payload = {
                "quote_id": "q",
                "product_id": "crown",
                "price": 45,
                "base_price": 60,
                "reward_points": 15,
                "item_count": 1,
                "owned_count": 0,
                "expires_at": 4_000_000_000,
            }
        else:
            payload = {"saved": True}
        return HttpResponse(200, json.dumps(payload).encode())


def test_public_read_without_bearer_and_guest_cannot_mutate() -> None:
    transport = MarketTransport()
    gateway = HttpMarketGateway("https://accounts.test", cast(HttpClient, transport), lambda: "")
    assert not gateway.fetch_catalog().enabled
    assert "Authorization" not in transport.calls[0][3]
    with pytest.raises(SessionRevoked):
        gateway.create_quote("crown", True)
    assert len(transport.calls) == 1


def test_quote_sends_only_product_and_point_choice_and_purchase_reuses_same_key() -> None:
    transport = MarketTransport()
    access_token = "a" * 64
    register_session(access_token, "b" * 64)
    try:
        gateway = HttpMarketGateway(
            "https://accounts.test", cast(HttpClient, transport), lambda: access_token
        )
        gateway.fetch_catalog()
        assert "Authorization" not in transport.calls[-1][3]
        quote = gateway.create_quote("crown", True)
        assert quote.reward_points == 15 and quote.price == 45
        assert json.loads(transport.calls[-1][2]) == {"product_id": "crown", "use_points": True}
        assert "Nostalgia-Proof" in transport.calls[-1][3]
        for _ in range(2):
            gateway.purchase(quote, "stable-request")
            assert transport.calls[-1][3]["Idempotency-Key"] == "stable-request"
            assert json.loads(transport.calls[-1][2]) == {"quote_id": "q"}
    finally:
        forget_session(access_token)
