"""Dữ liệu thanh toán đã kiểm tra, tách khỏi trạng thái giao diện."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

PaymentStatus = Literal["pending", "paid", "expired", "cancelled"]


@dataclass(frozen=True, slots=True)
class PaymentOffer:
    offer_id: str
    amount: int
    regular_amount: int
    duration_months: int = 12
    lifetime: bool = False
    upgrade_credit: int = 0
    quote_id: str = ""
    eligible: bool = True
    upgrade: bool = False
    current_plan: str = ""

    @property
    def plan_name(self) -> str:
        return {1: "Plus", 6: "Pro", 12: "Max", 0: "Ultimate"}.get(self.duration_months, "Plus")


@dataclass(frozen=True, slots=True)
class PaymentOrder:
    order_id: str
    offer_id: str
    amount: int
    status: PaymentStatus
    expires_at: int
    bank_name: str = ""
    holder: str = ""
    account_number: str = ""
    transfer_memo: str = ""
    qr_image: str = ""
    checkout_url: str = ""
    active_until: int = 0
    lifetime: bool = False
    manual_review: bool = False
    submitted: bool = False
    payment_offer: PaymentOffer | None = None


@dataclass(frozen=True, slots=True)
class PaymentCheckout:
    offer: PaymentOffer
    order: PaymentOrder | None


class PaymentGateway(Protocol):
    """Client không tự cấp quyền: chỉ tạo đơn và hỏi trạng thái máy chủ."""

    def fetch_offer(self, offer_id: str = "") -> PaymentOffer: ...

    def create_order(self, offer: PaymentOffer, request_id: str) -> PaymentOrder: ...

    def fetch_current_order(self, offer: PaymentOffer) -> PaymentOrder | None: ...

    def fetch_order(self, order: PaymentOrder) -> PaymentOrder: ...


@runtime_checkable
class ManualPaymentGateway(Protocol):
    """Gửi yêu cầu duyệt; không có thao tác cấp quyền từ client."""

    def submit_transfer(self, order: PaymentOrder) -> PaymentOrder: ...
