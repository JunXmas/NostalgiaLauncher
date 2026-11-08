"""HTTP marketplace với proof hiện có; không gửi Google token vào Nos Client."""

import json
import re
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.marketplace.cache import sync_cosmetic_asset
from nostalgia.marketplace.parse import (
    parse_catalog,
    parse_order,
    parse_quote,
    parse_rewards,
    parse_wardrobe,
    rows,
)
from nostalgia.model.cosmetic import CosmeticAsset
from nostalgia.model.json_value import JsonValue, as_mapping
from nostalgia.model.marketplace import (
    CoinOrder,
    EquippedCosmetic,
    GameCosmeticSession,
    MarketAccount,
    MarketCatalog,
    MarketQuote,
    MarketRewards,
    Wardrobe,
)
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.net.session_proof import proof_headers


class HttpMarketGateway:
    def create_game_session(self, public_key: str) -> GameCosmeticSession:
        fields = as_mapping(
            self._request("POST", "/v1/marketplace/sessions", {"public_key": public_key})
        )
        capability = fields.get("capability")
        expires = fields.get("expires_at")
        if (
            not isinstance(capability, str)
            or not re.fullmatch("[a-f0-9]{64}", capability)
            or fields.get("public_key") != public_key
            or type(expires) is not int
        ):
            raise SocialError("Invalid cosmetic game session")
        equipped = []
        for raw_slot in rows(fields, "loadout"):
            slot = as_mapping(raw_slot)
            digest, category = slot.get("asset_hash"), slot.get("slot")
            if (
                category not in ("head", "top", "bottom", "feet", "back", "accessory")
                or not isinstance(digest, str)
                or not re.fullmatch("[a-f0-9]{64}", digest)
            ):
                raise SocialError("Invalid cosmetic loadout")
            equipped.append(EquippedCosmetic(category, digest))
        if len(equipped) > 6 or len({slot.slot for slot in equipped}) != len(equipped):
            raise SocialError("Invalid cosmetic slots")
        return GameCosmeticSession(capability, public_key, expires, tuple(equipped))

    def sync_asset(self, digest: str, cache_dir: Path) -> CosmeticAsset:
        return sync_cosmetic_asset(self._http_client, self.base_url, digest, cache_dir)

    def __init__(
        self, base_url: str, http_client: HttpClient, access_token: Callable[[], str]
    ) -> None:
        endpoint = urlsplit(base_url)
        if (
            endpoint.scheme != "https"
            or not endpoint.hostname
            or endpoint.query
            or endpoint.fragment
            or endpoint.username
            or endpoint.path not in ("", "/")
        ):
            raise SocialError("Invalid marketplace endpoint")
        self.base_url = base_url.rstrip("/")
        self._http_client, self._access_token = http_client, access_token

    def _request(
        self,
        method: str,
        path: str,
        document: JsonValue = None,
        *,
        request_id: str = "",
        public: bool = False,
    ) -> JsonValue:
        access_token = self._access_token() if not public else ""
        if not public and not access_token:
            raise SessionRevoked("Đăng nhập Google để mở ví và tủ đồ.")
        payload = json.dumps(document).encode() if document is not None else None
        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = "Bearer " + access_token
            headers.update(proof_headers(access_token, method, self.base_url + path, payload))
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if request_id:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", request_id):
                raise SocialError("Invalid idempotency key")
            headers["Idempotency-Key"] = request_id
        response = self._http_client.send(
            method, self.base_url + path, body=payload, headers=headers, max_bytes=1_000_000
        )
        if response.status == 401:
            raise SessionRevoked("Phiên đã hết hạn. Hãy đăng nhập lại.")
        if not response.is_ok:
            messages = {
                409: "Giá, số dư hoặc quyền sở hữu đã thay đổi. Hãy tải lại.",
                503: "Marketplace chưa được mở.",
                429: "Bạn thao tác quá nhanh. Hãy thử lại sau.",
            }
            raise SocialError(
                messages.get(
                    response.status,
                    "Không xác nhận được giao dịch. Hãy kiểm tra tủ đồ trước khi thử lại.",
                )
            )
        return decode_json(response.body, what="marketplace")

    def fetch_catalog(self) -> MarketCatalog:
        return parse_catalog(self._request("GET", "/v1/marketplace/catalog", public=True))

    def fetch_wardrobe(self) -> Wardrobe:
        return parse_wardrobe(self._request("GET", "/v1/marketplace/wardrobe"))

    def fetch_account(self) -> MarketAccount:
        return MarketAccount(self.fetch_wardrobe(), self.fetch_rewards(), self.fetch_topups())

    def fetch_rewards(self) -> MarketRewards:
        return parse_rewards(self._request("GET", "/v1/marketplace/rewards"))

    def claim_reward(self) -> MarketRewards:
        return parse_rewards(self._request("POST", "/v1/marketplace/rewards/claim", {}))

    def create_quote(self, product_id: str, use_points: bool = False) -> MarketQuote:
        return parse_quote(
            self._request(
                "POST",
                "/v1/marketplace/quotes",
                {"product_id": product_id, "use_points": use_points},
            )
        )

    def purchase(self, quote: MarketQuote, request_id: str) -> None:
        self._request(
            "POST", "/v1/marketplace/purchases", {"quote_id": quote.quote_id}, request_id=request_id
        )

    def equip(self, instance_id: str, slot: str) -> Wardrobe:
        return parse_wardrobe(
            self._request(
                "POST", "/v1/marketplace/equip", {"instance_id": instance_id, "slot": slot}
            )
        )

    def fetch_topups(self) -> tuple[CoinOrder, ...]:
        fields = as_mapping(self._request("GET", "/v1/marketplace/topups"))
        return tuple(parse_order(row) for row in rows(fields, "orders"))

    def create_topup(self, offer_id: str, request_id: str) -> CoinOrder:
        return parse_order(
            self._request(
                "POST", "/v1/marketplace/topups", {"offer_id": offer_id}, request_id=request_id
            )
        )

    def submit_topup(self, order_id: str) -> CoinOrder:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}", order_id):
            raise SocialError("Invalid order identifier")
        return parse_order(
            self._request("POST", "/v1/marketplace/topups/" + order_id + "/submit", {})
        )
