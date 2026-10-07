"""Authenticated transport shared by social operations, with request possession proof."""

from __future__ import annotations

import json

from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.net.session_proof import proof_headers


class SocialTransport:
    base_url: str
    access_token: str
    _http_client: HttpClient

    def _request(
        self, method: str, path: str, document: JsonValue = None, *, authenticated: bool = True
    ) -> JsonValue:
        headers = {"Accept": "application/json"}
        if authenticated:
            if not self.access_token:
                raise SessionRevoked("Cần đăng nhập Google để dùng bạn bè và Plus.")
            headers["Authorization"] = "Bearer " + self.access_token
        payload = json.dumps(document).encode() if document is not None else None
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if authenticated:
            headers.update(proof_headers(self.access_token, method, self.base_url + path, payload))
        response = self._http_client.send(
            method,
            self.base_url + path,
            headers=headers,
            body=payload,
            max_bytes=512_000 if path == "/v1/me" else 256_000,
        )
        if response.status == 401 and authenticated:
            raise SessionRevoked(
                "Phiên đã hết hạn hoặc tài khoản vừa đăng nhập trên máy khác. Hãy đăng nhập lại."
            )
        if not response.is_ok:
            messages = {
                403: "Không có quyền với tài khoản này.",
                404: "Không tìm thấy bạn hoặc lời mời đã hết hạn.",
                409: "Phòng không còn mở hoặc thao tác đã được thực hiện.",
                429: "Bạn thao tác quá nhanh. Hãy thử lại sau.",
                503: "Dịch vụ chưa sẵn sàng. Hãy thử lại sau.",
            }
            raise SocialError(
                messages.get(response.status, "Không xác nhận được với dịch vụ tài khoản.")
            )
        return decode_json(response.body, what="dịch vụ tài khoản")
