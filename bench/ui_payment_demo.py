"""Nguồn dữ liệu chỉ để duyệt UI; QR chứa chữ DEMO, không phải lệnh chuyển tiền."""

from __future__ import annotations

import base64
import time
from dataclasses import replace

from nostalgia.api import PaymentOffer, PaymentOrder
from nostalgia.auth.qr import encode_qr, qr_png_bytes


class DemoPaymentGateway:
    """Không nối ngân hàng, không cấp quyền thật và không dùng ở điểm vào phát hành."""

    def __init__(self) -> None:
        self.status = "pending"
        self.creations: list[str] = []
        self.checks = 0

    def fetch_offer(self) -> PaymentOffer:
        return PaymentOffer("demo-year-intro", 69_000, 99_000)

    def create_order(self, offer: PaymentOffer, request_id: str) -> PaymentOrder:
        self.creations.append(request_id)
        image_bytes = qr_png_bytes(encode_qr("NOSTALGIA PLUS DEMO - NO PAYMENT"), scale=6)
        return PaymentOrder(
            "DEMO_20261006",
            offer.offer_id,
            offer.amount,
            "pending",
            int(time.time()) + 900,
            "Ngân hàng mẫu",
            "TAI KHOAN MINH HOA",
            "0000000000",
            "NOSTALGIA DEMO 20261006",
            "data:image/png;base64," + base64.b64encode(image_bytes).decode(),
        )

    def fetch_current_order(self, _offer: PaymentOffer) -> PaymentOrder | None:
        return None

    def fetch_order(self, order: PaymentOrder) -> PaymentOrder:
        self.checks += 1
        if self.status == "paid":
            return replace(order, status="paid", active_until=int(time.time()) + 365 * 86400)
        if self.status == "expired":
            return replace(order, status="expired")
        if self.status == "cancelled":
            return replace(order, status="cancelled")
        return order
