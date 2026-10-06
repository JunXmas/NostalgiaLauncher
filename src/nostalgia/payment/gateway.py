"""Gọi dịch vụ Plus qua HTTPS; không nhúng khóa cổng thanh toán trong launcher."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from nostalgia.errors import PaymentError
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.payment.model import PaymentOffer, PaymentOrder
from nostalgia.payment.parse import identifier, parse_offer, parse_order


class HttpPaymentGateway:
    """Nhận phiên tài khoản ủng hộ đã được backend xác thực, không dùng token Minecraft."""

    def __init__(self, base_url: str, session_token: str, http_client: HttpClient) -> None:
        parts = urlsplit(base_url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or not session_token
            or any(c.isspace() for c in session_token)
        ):
            raise PaymentError("Cấu hình dịch vụ thanh toán không hợp lệ.")
        self._base_url = base_url.rstrip("/")
        self._session_token = session_token
        self._http_client = http_client

    def fetch_offer(self, offer_id: str = "") -> PaymentOffer:
        query = "?offer_id=" + identifier(offer_id) if offer_id else ""
        return parse_offer(self._request("GET", "/v1/plus/offer" + query))

    def create_order(self, offer: PaymentOffer, request_id: str) -> PaymentOrder:
        document = self._request(
            "POST",
            "/v1/plus/orders",
            body=json.dumps({"offer_id": offer.offer_id}).encode(),
            request_id=identifier(request_id),
        )
        return parse_order(document, offer)

    def fetch_current_order(self, offer: PaymentOffer) -> PaymentOrder | None:
        document = self._request("GET", "/v1/plus/orders/current")
        return None if document is None else parse_order(document, offer)

    def fetch_order(self, order: PaymentOrder) -> PaymentOrder:
        document = self._request("GET", "/v1/plus/orders/" + identifier(order.order_id))
        current = parse_order(
            document,
            PaymentOffer(
                order.offer_id,
                order.amount,
                order.amount,
                0 if order.lifetime else 12,
                order.lifetime,
            ),
        )
        if current.order_id != order.order_id:
            raise PaymentError("Máy chủ trả về một đơn thanh toán khác.")
        if (
            current.expires_at != order.expires_at
            or (order.status != "pending" and current.status != order.status)
            or (
                current.status == "pending"
                and (current.account_number, current.transfer_memo, current.holder)
                != (order.account_number, order.transfer_memo, order.holder)
            )
        ):
            raise PaymentError("Thông tin đơn thanh toán đã thay đổi; hãy liên hệ hỗ trợ.")
        return current

    def _request(
        self, method: str, path: str, *, body: bytes | None = None, request_id: str = ""
    ) -> JsonValue:
        headers = {"Authorization": "Bearer " + self._session_token, "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Idempotency-Key"] = request_id
        response = self._http_client.send(
            method, self._base_url + path, body=body, headers=headers, max_bytes=128_000
        )
        if response.status in (401, 403):
            raise PaymentError(
                "Phiên tài khoản ủng hộ hết hạn. Hãy đăng nhập lại trước khi thanh toán."
            )
        if not response.is_ok:
            raise PaymentError("Không xác nhận được với dịch vụ thanh toán. Hãy thử lại sau.")
        return decode_json(response.body, what="phản hồi thanh toán")
