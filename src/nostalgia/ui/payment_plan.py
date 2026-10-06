"""Giá hiển thị trước xác nhận API; không cấp quyền hoặc cho tạo đơn chưa nạp offer."""

from nostalgia.api import PaymentCheckout, PaymentGateway, PaymentOffer


def resolve_preview_offer(months: int) -> PaymentOffer | None:
    prices = {
        1: ("plus-month-v1", 29000),
        6: ("plus-half-year-v1", 69000),
        12: ("plus-year-v2", 109000),
        0: ("plus-lifetime-v1", 209000),
    }
    if months not in prices:
        return None
    offer_id, amount = prices[months]
    return PaymentOffer(offer_id, amount, amount, months, months == 0)


def fetch_checkout(gateway: PaymentGateway, selected_offer_id: str) -> PaymentCheckout:
    offer = gateway.fetch_offer(selected_offer_id) if selected_offer_id else gateway.fetch_offer()
    order = gateway.fetch_current_order(offer)
    if order is not None and order.offer_id != offer.offer_id:
        offer = gateway.fetch_offer(order.offer_id)
    if order is not None and order.status in ("expired", "cancelled"):
        order = None
    return PaymentCheckout(offer, order)
