"""Payment layout simulation: contains no bank account, checkout URL or real VietQR."""

from __future__ import annotations

import base64
import importlib
import io
import time
from dataclasses import replace

from nostalgia.payment.model import PaymentOffer, PaymentOrder
from nostalgia.ui.payment_plan import resolve_preview_offer


class ReviewPayment:
    def __init__(self) -> None:
        self.order: PaymentOrder | None = None
        self.paid = False

    def fetch_offer(self, offer_id: str = "") -> PaymentOffer:
        for lifetime in (False, True):
            offer = resolve_preview_offer(lifetime)
            if not offer_id or offer.offer_id == offer_id:
                return offer
        raise ValueError("Gói TEST không hợp lệ.")

    def create_order(self, offer: PaymentOffer, request_id: str) -> PaymentOrder:
        qr = importlib.import_module("segno").make_qr("nostalgia-draft://simulation/no-payment")
        output = io.BytesIO()
        qr.save(output, kind="png", scale=5, border=4)
        self.paid = False
        self.order = PaymentOrder(
            "TEST-" + request_id[:12],
            offer.offer_id,
            offer.amount,
            "pending",
            int(time.time()) + 600,
            bank_name="MÔ PHỎNG · KHÔNG CHUYỂN TIỀN",
            holder="Nostalgia Draft",
            transfer_memo="TEST, không phải mã chuyển khoản",
            qr_image="data:image/png;base64," + base64.b64encode(output.getvalue()).decode(),
            lifetime=offer.lifetime,
            payment_offer=offer,
        )
        return self.order

    def fetch_current_order(self, offer: PaymentOffer) -> PaymentOrder | None:
        return self.order if self.order and self.order.offer_id == offer.offer_id else None

    def fetch_order(self, order: PaymentOrder) -> PaymentOrder:
        if self.paid:
            return replace(
                order,
                status="paid",
                active_until=0 if order.lifetime else int(time.time()) + 365 * 86400,
            )
        return order
