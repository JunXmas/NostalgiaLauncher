"""Dữ liệu phản hồi máy chủ giả; mã QR không chứa lệnh chuyển tiền."""

from __future__ import annotations

import base64
import time

from nostalgia.auth.qr import encode_qr, qr_png_bytes
from nostalgia.model.json_value import JsonValue


def offer_document() -> dict[str, JsonValue]:
    return {
        "offer_id": "intro-year",
        "amount": 69_000,
        "regular_amount": 99_000,
        "duration_months": 12,
        "currency": "VND",
    }


def order_document(status: str = "pending") -> dict[str, JsonValue]:
    png = qr_png_bytes(encode_qr("DEMO NO PAYMENT"), scale=6)
    return {
        "order_id": "order_123",
        "offer_id": "intro-year",
        "amount": 69_000,
        "currency": "VND",
        "status": status,
        "expires_at": int(time.time()) + 900,
        "active_until": int(time.time()) + 365 * 86400 if status == "paid" else 0,
        "bank_name": "Ngân hàng mẫu",
        "holder": "TAI KHOAN MINH HOA",
        "account_number": "0000000000",
        "transfer_memo": "DEMO ORDER 123",
        "qr_image": "data:image/png;base64," + base64.b64encode(png).decode(),
        "checkout_url": "https://pay.payos.vn/web/order_123",
    }
