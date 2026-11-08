"""Thao tác rõ ràng, giữ khóa giao dịch khi lỗi mạng để thử lại không cấp trùng."""

import uuid
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from nostalgia.errors import NostalgiaError
from nostalgia.model.marketplace import (
    CoinOrder,
    MarketAccount,
    MarketCatalog,
    MarketGateway,
    MarketQuote,
    MarketRewards,
    Wardrobe,
)
from nostalgia.ui.market_state import MarketState
from nostalgia.ui.social_bridge import SocialBridge


class MarketBridge(MarketState):
    _arrived = Signal(int, str, object, str)

    def __init__(
        self, gateway: MarketGateway | None, social: SocialBridge, parent: QObject
    ) -> None:
        super().__init__(parent)
        self.initialize(gateway)
        self._social = social
        self._arrived.connect(self._apply)
        social.sessionChanged.connect(self._reset)

    @Slot()
    def _reset(self) -> None:
        self.next_generation()
        self._wardrobe, self._orders, self._quote = Wardrobe(), (), None
        self._rewards = MarketRewards()
        self._request_id = self._topup_request_id = self._topup_offer_id = self._topup_order_id = ""
        self.changed.emit()

    def _request(self, operation: str, work: Callable[[], object]) -> None:
        if self.busy or self._gateway is None:
            return
        generation = self.next_generation()

        def perform() -> None:
            try:
                self._arrived.emit(generation, operation, work(), "")
            except (NostalgiaError, OSError) as error:
                self._arrived.emit(generation, operation, None, str(error))

        self.run_in_background(perform, "Đang đồng bộ marketplace…")

    @Slot()
    def refresh(self) -> None:
        gateway = self._gateway
        if gateway:
            self._request("catalog", gateway.fetch_catalog)

    @Slot()
    def refreshWallet(self) -> None:
        gateway = self._gateway
        if gateway and self._social.signedIn:
            self._request("account", gateway.fetch_account)

    @Slot()
    def refreshOrders(self) -> None:
        gateway = self._gateway
        if gateway and self._social.signedIn:
            self._request("account", gateway.fetch_account)

    @Slot()
    def claimReward(self) -> None:
        gateway = self._gateway
        if gateway and self._social.signedIn:
            self._request("reward", gateway.claim_reward)

    @Slot(str, bool)
    def quote(self, product_id: str, use_points: bool = False) -> None:
        gateway = self._gateway
        if gateway and self._social.signedIn:
            self._request("quote", lambda: gateway.create_quote(product_id, use_points))

    @Slot()
    def buy(self) -> None:
        gateway, quote = self._gateway, self._quote
        if gateway and quote and self._social.signedIn:
            if not self._request_id:
                self._request_id = uuid.uuid4().hex
            request_id = self._request_id

            def purchase() -> MarketAccount:
                gateway.purchase(quote, request_id)
                return gateway.fetch_account()

            self._request("purchased", purchase)

    @Slot()
    def cancelQuote(self) -> None:
        if not self.busy:
            self._quote, self._request_id = None, ""
            self.changed.emit()

    @Slot(str, str)
    def equip(self, instance_id: str, slot: str) -> None:
        gateway = self._gateway
        if gateway and self._social.signedIn:
            self._request("wardrobe", lambda: gateway.equip(instance_id, slot))

    @Slot(str)
    def topup(self, offer_id: str) -> None:
        gateway = self._gateway
        if gateway and self._social.signedIn:
            if self._topup_offer_id != offer_id:
                self._topup_offer_id, self._topup_request_id = offer_id, uuid.uuid4().hex
            request_id = self._topup_request_id
            self._request("topup", lambda: gateway.create_topup(offer_id, request_id))

    @Slot(str)
    def submitTopup(self, order_id: str) -> None:
        gateway = self._gateway
        if gateway and self._social.signedIn:
            self._request("topup", lambda: gateway.submit_topup(order_id))

    @Slot(int, str, object, str)
    def _apply(self, generation: int, operation: str, payload: object, error: str) -> None:
        if not self.is_current(generation):
            return
        self._note = error
        if isinstance(payload, MarketCatalog):
            self._catalog = payload
        elif isinstance(payload, MarketRewards):
            self._rewards = payload
        elif isinstance(payload, MarketAccount):
            self._wardrobe, self._rewards, self._orders = (
                payload.wardrobe,
                payload.rewards,
                payload.orders,
            )
            if any(
                order.order_id == self._topup_order_id and order.status in ("paid", "rejected")
                for order in payload.orders
            ):
                self._topup_request_id = self._topup_offer_id = self._topup_order_id = ""
            if operation == "purchased":
                self._quote, self._request_id = None, ""
                self._note = "Đã mua. Bạn có thể trang bị trong Tủ đồ."
        elif isinstance(payload, Wardrobe):
            self._wardrobe = payload
            self.appearanceChanged.emit()
        elif isinstance(payload, MarketQuote):
            self._quote, self._request_id = payload, uuid.uuid4().hex
        elif isinstance(payload, CoinOrder):
            self._topup_order_id = payload.order_id
            self._orders = (
                payload,
                *(order for order in self._orders if order.order_id != payload.order_id),
            )
        elif isinstance(payload, tuple) and all(isinstance(order, CoinOrder) for order in payload):
            self._orders = payload
        self.changed.emit()
