"""Asset tự vẽ và gateway cô lập cho kiểm preview; không chạm dịch vụ thật."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from nostalgia.marketplace.asset import parse_asset
from nostalgia.model.cosmetic import CosmeticAsset
from nostalgia.model.marketplace import (
    CoinOffer,
    CoinOrder,
    MarketAccount,
    MarketCatalog,
    MarketProduct,
    MarketQuote,
    MarketRewards,
    Wardrobe,
)

ASSET_PAYLOAD = json.dumps(
    {
        "schema_version": 1,
        "texture_png": (
            "iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAYAAACp8Z5+AAAAEklEQVR4nGOoCLj0HxkzkC4A"
            "AHT3KZFtRs3NAAAAAElFTkSuQmCC"
        ),
        "parts": [
            {
                "bone": "head",
                "model": {
                    "format": 1,
                    "texture": "nosclient:cosmetic",
                    "fps": 60,
                    "duration": 1,
                    "nodes": [
                        {
                            "parent": -1,
                            "translation": [0, 0, 0],
                            "rotation": [0, 0, 0, 1],
                            "vertices": [
                                -0.3,
                                1.9,
                                -0.3,
                                0,
                                0,
                                0,
                                0,
                                1,
                                0.3,
                                1.9,
                                -0.3,
                                1,
                                0,
                                0,
                                0,
                                1,
                                0.3,
                                2.15,
                                -0.3,
                                1,
                                1,
                                0,
                                0,
                                1,
                                -0.3,
                                2.15,
                                -0.3,
                                0,
                                1,
                                0,
                                0,
                                1,
                            ],
                        }
                    ],
                },
            }
        ],
    }
).encode()
ASSET_HASH = hashlib.sha256(ASSET_PAYLOAD).hexdigest()


class MarketFixture:
    def __init__(self) -> None:
        self.product = MarketProduct(
            "sample-crown",
            "Amethyst Crown",
            "Vương miện tím",
            "A test crown",
            "Vương miện kiểm thử",
            "head",
            60,
            1,
            ASSET_HASH,
        )
        self._wardrobe = Wardrobe(100)
        self.keys: list[str] = []
        self.rewards = MarketRewards(True, True, False, 40, 40, 25, 30, 4_000_000_000)

    def fetch_catalog(self) -> MarketCatalog:
        return MarketCatalog(True, (self.product,), (CoinOffer("test-coins", 10000, 100),))

    def fetch_wardrobe(self) -> Wardrobe:
        return self._wardrobe

    def sync_asset(self, digest: str, cache_dir: Path) -> CosmeticAsset:
        assert isinstance(cache_dir, Path)
        assert digest == ASSET_HASH
        return parse_asset(ASSET_PAYLOAD)

    def fetch_account(self) -> MarketAccount:
        return MarketAccount(self._wardrobe, self.rewards, self.fetch_topups())

    def claim_reward(self) -> MarketRewards:
        self.rewards = replace(self.rewards, claimed_today=True, balance=self.rewards.balance + 40)
        return self.rewards

    def create_quote(self, product_id: str, use_points: bool = False) -> MarketQuote:
        return MarketQuote(
            "quote-one",
            product_id,
            45 if use_points else 60,
            4_000_000_000,
            base_price=60,
            reward_points=15 if use_points else 0,
        )

    def purchase(self, quote: MarketQuote, request_id: str) -> None:
        self.keys.append(request_id)
        self._wardrobe = Wardrobe(
            100 - quote.price, (replace(self.product, instance_id="owned-one"),)
        )
        self.rewards = replace(self.rewards, balance=self.rewards.balance - quote.reward_points)

    def equip(self, instance_id: str, slot: str) -> Wardrobe:
        self._wardrobe = replace(
            self._wardrobe,
            owned=tuple(
                replace(product, equipped_slot=slot if instance_id else "")
                for product in self._wardrobe.owned
            ),
        )
        return self._wardrobe

    def fetch_topups(self) -> tuple[CoinOrder, ...]:
        return ()

    def create_topup(self, offer_id: str, request_id: str) -> CoinOrder:
        assert offer_id and request_id
        return CoinOrder(
            "order-one", 10000, 100, "pending", "123456789", "TEST", "NSC TEST", "test-qr"
        )

    def submit_topup(self, order_id: str) -> CoinOrder:
        assert order_id
        return replace(self.create_topup("test-coins", "request-one"), status="submitted")
