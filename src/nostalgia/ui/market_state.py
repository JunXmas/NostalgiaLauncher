"""Trạng thái hiển thị marketplace; dữ liệu quyền đến từ gateway."""

from dataclasses import asdict
from typing import Any

from PySide6.QtCore import Property, Signal

from nostalgia.model.marketplace import (
    CoinOrder,
    MarketCatalog,
    MarketGateway,
    MarketQuote,
    MarketRewards,
    Wardrobe,
)
from nostalgia.ui.worker import WorkerBridge


class MarketState(WorkerBridge):
    changed = Signal()
    appearanceChanged = Signal()
    _gateway: MarketGateway | None

    def initialize(self, gateway: MarketGateway | None) -> None:
        self._gateway = gateway
        self._catalog = MarketCatalog()
        self._wardrobe = Wardrobe()
        self._rewards = MarketRewards()
        self._orders: tuple[CoinOrder, ...] = ()
        self._quote: MarketQuote | None = None
        self._note = ""
        self._request_id = ""
        self._topup_request_id = ""
        self._topup_offer_id = ""
        self._topup_order_id = ""

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        return {
            "configured": self._gateway is not None,
            "enabled": self._catalog.enabled,
            "balance": self._wardrobe.balance,
            "rewards": asdict(self._rewards),
            "products": [asdict(p) for p in self._catalog.products],
            "owned": [asdict(p) for p in self._wardrobe.owned],
            "coinOffers": [asdict(p) for p in self._catalog.coin_offers],
            "orders": [asdict(order) for order in self._orders],
            "quote": asdict(self._quote) if self._quote else {},
            "note": self._note,
        }
