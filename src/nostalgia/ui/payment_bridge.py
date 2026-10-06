"""Trạng thái thanh toán; không có slot tự đánh dấu đã trả hay mở khóa Plus."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from nostalgia.api import PaymentCheckout, PaymentGateway, PaymentOffer, PaymentOrder
from nostalgia.errors import NostalgiaError
from nostalgia.ui.worker import WorkerBridge


class PaymentBridge(WorkerBridge):
    changed = Signal()
    _arrived = Signal(int, str, object, str)

    def __init__(
        self,
        gateway: PaymentGateway | None = None,
        *,
        demonstration: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._gateway = gateway
        self._demonstration = demonstration
        self._offer = PaymentOffer("", 109_000, 109_000)
        self._selected_offer_id = ""
        self._offer_loaded = False
        self._order: PaymentOrder | None = None
        self._request_id = uuid.uuid4().hex
        self._error = ""
        self._watching = False
        self._arrived.connect(self._apply)
        self._poll = QTimer(self)
        self._poll.setInterval(5000)
        self._poll.timeout.connect(self.checkPayment)
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self.changed.emit)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        order = self._order
        remaining = max(0, order.expires_at - int(time.time())) if order else 0
        status: str = order.status if order else "offer" if self._gateway else "unavailable"
        if order and status == "pending" and not remaining:
            status = "verifying"
        return {
            "stage": status,
            "demonstration": self._demonstration,
            "available": self._offer_loaded and self._gateway is not None,
            "amount": self._offer.amount,
            "regularAmount": self._offer.regular_amount,
            "months": self._offer.duration_months,
            "lifetime": self._offer.lifetime,
            "error": self._error,
            "orderId": order.order_id if order else "",
            "bank": order.bank_name if order else "",
            "holder": order.holder if order else "",
            "accountNumber": order.account_number if order else "",
            "memo": order.transfer_memo if order else "",
            "qr": order.qr_image if order and status == "pending" else "",
            "checkoutUrl": order.checkout_url if order and status == "pending" else "",
            "remaining": remaining,
            "activeUntil": datetime.fromtimestamp(order.active_until, UTC).strftime("%d/%m/%Y")
            if order and order.status == "paid" and not self._offer.lifetime
            else "Không hết hạn"
            if order and order.status == "paid"
            else "",
        }

    def set_gateway(self, gateway: PaymentGateway | None) -> None:
        self.next_generation()
        self._poll.stop()
        self._clock.stop()
        self._gateway, self._order = gateway, None
        self._offer_loaded = False
        self._request_id = uuid.uuid4().hex
        self._error = ""
        self.changed.emit()

    @Slot(int)
    def selectPlan(self, months: int) -> None:
        prices = {
            1: ("plus-month-v1", 29_000),
            6: ("plus-half-year-v1", 69_000),
            12: ("plus-year-v2", 109_000),
            0: ("plus-lifetime-v1", 209_000),
        }
        if months not in prices or self.busy or self._order is not None:
            return
        offer_id, amount = prices[months]
        self._selected_offer_id = offer_id
        self._offer = PaymentOffer(offer_id, amount, amount, months, months == 0)
        self._offer_loaded = False
        self._request_id = uuid.uuid4().hex
        self.changed.emit()
        self.loadOffer()

    @Slot(bool)
    def setWatching(self, watching: bool) -> None:
        self._watching = watching
        if not watching:
            self._poll.stop()
            self._clock.stop()
        else:
            if not self._order:
                self.loadOffer()
            else:
                self.checkPayment()
            self._sync_timers()

    @Slot()
    def loadOffer(self) -> None:
        gateway = self._gateway
        if self.busy or self._order or gateway is None:
            return

        def fetch_checkout() -> PaymentCheckout:
            offer = (
                gateway.fetch_offer(self._selected_offer_id)
                if self._selected_offer_id
                else gateway.fetch_offer()
            )
            order = gateway.fetch_current_order(offer)
            if order is not None and order.status in ("expired", "cancelled"):
                order = None
            return PaymentCheckout(offer, order)

        self._request("offer", fetch_checkout)

    @Slot()
    def createOrder(self) -> None:
        gateway = self._gateway
        if self.busy or self._order or not self._offer_loaded or gateway is None:
            return
        offer, request_id = self._offer, self._request_id
        self._request("order", lambda: gateway.create_order(offer, request_id))

    @Slot()
    def checkPayment(self) -> None:
        gateway, order = self._gateway, self._order
        if self.busy or gateway is None or order is None or order.status != "pending":
            return
        self._request("order", lambda: gateway.fetch_order(order))

    @Slot()
    def newOrder(self) -> None:
        if self.busy or self._order is None or self._order.status not in ("expired", "cancelled"):
            return
        self._order = None
        self._offer_loaded = False
        self._request_id = uuid.uuid4().hex
        self._error = ""
        self.changed.emit()
        self.loadOffer()

    @Slot(str)
    def copyField(self, field: str) -> None:
        order = self._order
        if order is None:
            return
        if field == "orderId":
            QGuiApplication.clipboard().setText(order.order_id)
            return
        if order.status != "pending" or order.expires_at <= time.time():
            return
        values = {
            "amount": str(order.amount),
            "accountNumber": order.account_number,
            "memo": order.transfer_memo,
        }
        if field in values:
            QGuiApplication.clipboard().setText(values[field])

    def _request(self, operation: str, work: Callable[[], PaymentCheckout | PaymentOrder]) -> None:
        generation = self.next_generation()
        self._error = ""
        self.changed.emit()

        def perform() -> None:
            try:
                payload = work()
            except NostalgiaError as exc:
                self._arrived.emit(generation, operation, None, str(exc))
            except Exception:
                self._arrived.emit(generation, operation, None, "Không kết nối được. Hãy thử lại.")
            else:
                self._arrived.emit(generation, operation, payload, "")

        self.run_in_background(perform, "Đang xác nhận với dịch vụ thanh toán")

    def _apply(self, generation: int, operation: str, payload: object, error: str) -> None:
        if not self.is_current(generation):
            return
        self._error = error
        if not error:
            if operation == "offer" and isinstance(payload, PaymentCheckout):
                self._offer = payload.offer
                self._order = payload.order
                self._offer_loaded = True
            elif isinstance(payload, PaymentOrder):
                self._order = payload
        self._sync_timers()
        self.changed.emit()

    def _sync_timers(self) -> None:
        active = self._watching and self._order is not None and self._order.status == "pending"
        for timer in (self._poll, self._clock):
            if active:
                timer.start()
            else:
                timer.stop()
