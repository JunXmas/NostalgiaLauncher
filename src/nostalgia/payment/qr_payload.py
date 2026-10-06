"""Vẽ QR VietQR payOS trong launcher; không gửi mã chuyển khoản tới dịch vụ ảnh."""

from __future__ import annotations

import base64
import importlib
import io

from nostalgia.errors import PaymentError


def render_payment_qr(value: str) -> str:
    if not value.isascii() or not 1 <= len(value) <= 512 or not value.startswith("000201"):
        raise PaymentError("Nội dung QR thanh toán không hợp lệ.")
    try:
        segno = importlib.import_module("segno")
        qr = segno.make_qr(value, error="m")
        output = io.BytesIO()
        width = len(qr.matrix) + 8
        qr.save(output, kind="png", scale=256 // width, border=4)
    except (ImportError, ValueError) as error:
        raise PaymentError("Không vẽ được QR thanh toán; hãy kiểm tra bộ cài.") from error
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()
