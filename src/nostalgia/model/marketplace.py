"""Hợp đồng dữ liệu marketplace; không có cờ mở quyền cục bộ."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from nostalgia.model.cosmetic import CosmeticAsset


@dataclass(frozen=True, slots=True)
class MarketProduct:
    product_id: str
    name_en: str
    name_vi: str
    description_en: str
    description_vi: str
    slot: str
    price: int
    revision: int
    asset_hash: str
    instance_id: str = ""
    equipped_slot: str = ""
    product_kind: str = "item"
    members: tuple["MarketProduct", ...] = ()


@dataclass(frozen=True, slots=True)
class CoinOffer:
    offer_id: str
    amount: int
    coins: int


@dataclass(frozen=True, slots=True)
class MarketCatalog:
    enabled: bool = False
    products: tuple[MarketProduct, ...] = ()
    coin_offers: tuple[CoinOffer, ...] = ()


@dataclass(frozen=True, slots=True)
class Wardrobe:
    balance: int = 0
    owned: tuple[MarketProduct, ...] = ()


@dataclass(frozen=True, slots=True)
class MarketQuote:
    quote_id: str
    product_id: str
    price: int
    expires_at: int
    item_count: int = 1
    owned_count: int = 0
    base_price: int = 0
    reward_points: int = 0


@dataclass(frozen=True, slots=True)
class CoinOrder:
    order_id: str
    amount: int
    coins: int
    status: str
    bank_account: str
    bank_holder: str
    memo: str
    qr_payload: str
    qr_image: str = ""


@dataclass(frozen=True, slots=True)
class MarketRewards:
    enabled: bool = False
    member: bool = False
    claimed_today: bool = False
    balance: int = 0
    daily_points: int = 0
    max_percent: int = 0
    expiry_days: int = 0
    next_claim_at: int = 0
    next_expiry_at: int = 0
    expiring_points: int = 0


@dataclass(frozen=True, slots=True)
class MarketAccount:
    wardrobe: Wardrobe
    rewards: MarketRewards
    orders: tuple[CoinOrder, ...]


class MarketGateway(Protocol):
    def create_game_session(self, public_key: str) -> "GameCosmeticSession": ...
    def sync_asset(self, digest: str, cache_dir: Path) -> CosmeticAsset: ...
    def fetch_catalog(self) -> MarketCatalog: ...
    def fetch_wardrobe(self) -> Wardrobe: ...
    def fetch_account(self) -> MarketAccount: ...
    def claim_reward(self) -> MarketRewards: ...
    def create_quote(self, product_id: str, use_points: bool = False) -> MarketQuote: ...
    def purchase(self, quote: MarketQuote, request_id: str) -> None: ...
    def equip(self, instance_id: str, slot: str) -> Wardrobe: ...
    def fetch_topups(self) -> tuple[CoinOrder, ...]: ...
    def create_topup(self, offer_id: str, request_id: str) -> CoinOrder: ...
    def submit_topup(self, order_id: str) -> CoinOrder: ...


@dataclass(frozen=True, slots=True)
class EquippedCosmetic:
    slot: str
    asset_hash: str


@dataclass(frozen=True, slots=True)
class GameCosmeticSession:
    capability: str
    public_key: str
    expires_at: int
    loadout: tuple[EquippedCosmetic, ...]
