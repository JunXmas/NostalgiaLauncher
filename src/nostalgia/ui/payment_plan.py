"""Giá hiển thị trước xác nhận API; không cấp quyền hoặc cho tạo đơn chưa nạp offer."""

import logging
import time
from datetime import UTC, datetime
from typing import Any

from nostalgia.api import (
    OFFERS,
    ManualPaymentGateway,
    PaymentCheckout,
    PaymentGateway,
    PaymentOffer,
    PaymentOrder,
)
from nostalgia.errors import PaymentError

logger = logging.getLogger(__name__)


def resolve_preview_offer(lifetime: bool) -> PaymentOffer:
    return next(offer for offer in OFFERS if offer.lifetime is lifetime)


def fetch_offer(gateway: PaymentGateway, selected_offer_id: str) -> PaymentOffer:
    """Máy chủ chưa biết gói đã chọn (Worker còn bảng giá cũ) thì dùng gói mặc định của nó."""
    if selected_offer_id:
        try:
            return gateway.fetch_offer(selected_offer_id)
        except PaymentError as error:
            logger.warning(
                "Máy chủ không nhận gói %s, dùng gói mặc định: %s", selected_offer_id, error
            )
    return gateway.fetch_offer()


def fetch_checkout(gateway: PaymentGateway, selected_offer_id: str) -> PaymentCheckout:
    offer = fetch_offer(gateway, selected_offer_id)
    order = gateway.fetch_current_order(offer)
    if order is not None and order.offer_id != offer.offer_id:
        offer = gateway.fetch_offer(order.offer_id)
    if order is not None and order.status in ("expired", "cancelled"):
        order = None
    if order is not None and order.payment_offer is not None:
        offer = order.payment_offer
    return PaymentCheckout(offer, order)


def send_manual_review(gateway: PaymentGateway, order: PaymentOrder) -> PaymentOrder:
    if not isinstance(gateway, ManualPaymentGateway):
        raise PaymentError("Dịch vụ này chưa hỗ trợ gửi yêu cầu duyệt.")
    return gateway.submit_transfer(order)


def describe_checkout(
    offer: PaymentOffer,
    order: PaymentOrder | None,
    *,
    gateway_available: bool,
    offer_loaded: bool,
    demonstration: bool,
    error: str,
) -> dict[str, Any]:
    remaining = max(0, order.expires_at - int(time.time())) if order else 0
    status: str = order.status if order else "offer" if gateway_available else "unavailable"
    if order and status == "pending" and order.manual_review and order.submitted:
        status = "reviewing"
    elif order and status == "pending" and not remaining:
        status = "verifying"
    return {
        "stage": status,
        "demonstration": demonstration,
        "available": offer_loaded and gateway_available and offer.eligible,
        "amount": offer.amount,
        "upgradeCredit": offer.upgrade_credit,
        "isUpgrade": offer.upgrade,
        "eligible": offer.eligible,
        "months": offer.duration_months,
        "lifetime": offer.lifetime,
        "error": error,
        "orderId": order.order_id if order else "",
        "bank": order.bank_name if order else "",
        "holder": order.holder if order else "",
        "accountNumber": order.account_number if order else "",
        "memo": order.transfer_memo if order else "",
        "qr": order.qr_image if order and status == "pending" else "",
        "checkoutUrl": order.checkout_url if order and status == "pending" else "",
        "remaining": remaining,
        "manualReview": order.manual_review if order else False,
        "submitted": order.submitted if order else False,
        "activeUntil": datetime.fromtimestamp(order.active_until, UTC).strftime("%d/%m/%Y")
        if order and order.status == "paid" and not offer.lifetime
        else "Không hết hạn"
        if order and order.status == "paid"
        else "",
    }
