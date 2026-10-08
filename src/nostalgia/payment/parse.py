"""Từ chối giá, trạng thái, ảnh hoặc địa chỉ thanh toán không hợp lệ."""

from __future__ import annotations

import base64
import binascii
import re
import struct
from typing import cast
from urllib.parse import urlsplit

from nostalgia.errors import PaymentError
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping, as_string
from nostalgia.payment.model import PaymentOffer, PaymentOrder, PaymentStatus
from nostalgia.payment.qr_payload import render_payment_qr


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value):
        raise PaymentError("Máy chủ trả mã đơn không hợp lệ.")
    return value


def checkout_url(value: str) -> str:
    if not value:
        return ""
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or parts.netloc != "pay.payos.vn"
        or parts.username
        or parts.password
        or len(value) > 512
    ):
        raise PaymentError("Địa chỉ thanh toán không hợp lệ.")
    return value


def parse_offer(document: JsonValue) -> PaymentOffer:
    fields = as_mapping(document)
    amount = as_integer(fields.get("amount"))
    regular = as_integer(fields.get("regular_amount"))
    months = as_integer(fields.get("duration_months"))
    lifetime = fields.get("lifetime", False)
    credit = as_integer(fields.get("upgrade_credit", 0))
    upgrade = fields.get("upgrade", False)
    eligible = fields.get("eligible", True)
    quote_id = as_string(fields.get("quote_id")) or ""
    valid_duration = isinstance(lifetime, bool) and (
        months == 0 if lifetime else months in (1, 6, 12)
    )
    if (
        fields.get("currency") != "VND"
        or amount is None
        or regular is None
        or not 0 <= amount <= regular <= 10_000_000
        or regular <= 0
        or not isinstance(upgrade, bool)
        or not isinstance(eligible, bool)
        or credit is None
        or not 0 <= credit <= regular
        or (upgrade and credit != regular - amount)
        or (amount == 0 and not (upgrade and credit == regular))
        or not valid_duration
    ):
        raise PaymentError("Gói thanh toán không hợp lệ; hãy thử lại sau.")
    return PaymentOffer(
        identifier(as_string(fields.get("offer_id")) or ""),
        amount,
        regular,
        months or 0,
        lifetime is True,
        credit,
        identifier(quote_id) if quote_id else "",
        eligible is True,
        upgrade is True,
        as_string(fields.get("current_plan")) or "",
    )


def parse_order(document: JsonValue, offer: PaymentOffer) -> PaymentOrder:
    fields = as_mapping(document)
    status = as_string(fields.get("status")) or ""
    manual_review = fields.get("manual_review", False)
    submitted = fields.get("submitted", False)
    expires_at = as_integer(fields.get("expires_at")) or 0
    recorded_until = as_integer(fields.get("active_until"))
    active_until = recorded_until or 0
    if (
        not isinstance(manual_review, bool)
        or not isinstance(submitted, bool)
        or (submitted and not manual_review)
        or fields.get("offer_id") != offer.offer_id
        or as_integer(fields.get("amount")) != offer.amount
        or fields.get("currency") != "VND"
        or ("lifetime" in fields and fields["lifetime"] is not offer.lifetime)
        or status not in {"pending", "paid", "expired", "cancelled"}
        or (offer.amount == 0 and status != "paid")
        or not 0 < expires_at <= 4_102_444_800
        or (
            status == "paid"
            and (
                recorded_until is None
                or fields.get("lifetime", False) is not offer.lifetime
                or (active_until != 0 if offer.lifetime else not 0 < active_until <= 4_102_444_800)
            )
        )
    ):
        raise PaymentError("Thông tin xác nhận thanh toán không khớp với đơn.")
    strings = {
        field: as_string(fields.get(field)) or ""
        for field in ("bank_name", "holder", "account_number", "transfer_memo", "qr_image")
    }
    payment_url = checkout_url(as_string(fields.get("checkout_url")) or "")
    raw_qr = as_string(fields.get("qr_payload")) or ""
    if status == "pending" and raw_qr:
        strings["qr_image"] = render_payment_qr(raw_qr)
    if status == "pending":
        if strings["qr_image"]:
            if (
                not all(strings.values())
                or not strings["account_number"].isascii()
                or not strings["account_number"].isdigit()
                or any(len(strings[field]) > 150 for field in strings if field != "qr_image")
            ):
                raise PaymentError("Thông tin chuyển khoản chưa đầy đủ.")
            _validate_png(strings["qr_image"])
        elif not payment_url:
            raise PaymentError("Không có QR hoặc trang thanh toán được xác minh.")
    return PaymentOrder(
        identifier(as_string(fields.get("order_id")) or ""),
        offer.offer_id,
        offer.amount,
        cast(PaymentStatus, status),
        expires_at,
        **strings,
        checkout_url=payment_url,
        active_until=active_until,
        lifetime=offer.lifetime,
        manual_review=manual_review is True,
        submitted=submitted is True,
        payment_offer=offer,
    )


def _validate_png(value: str) -> None:
    prefix = "data:image/png;base64,"
    if not value.startswith(prefix) or len(value) > 90_000:
        raise PaymentError("Ảnh mã QR không hợp lệ.")
    try:
        payload = base64.b64decode(value.removeprefix(prefix), validate=True)
    except (ValueError, binascii.Error) as exc:
        raise PaymentError("Ảnh mã QR không hợp lệ.") from exc
    if len(payload) < 33 or payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise PaymentError("Ảnh mã QR không hợp lệ.")
    width, height = struct.unpack(">II", payload[16:24])
    if width != height or not 128 <= width <= 256:
        raise PaymentError("Kích thước mã QR không hợp lệ.")
