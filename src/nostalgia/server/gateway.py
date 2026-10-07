"""Server access comes from Google session and D1 membership, never a local tier flag."""

from __future__ import annotations

import json
import re
import time
from urllib.parse import urlsplit

from nostalgia.errors import ServerError, SessionRevoked
from nostalgia.model.json_value import JsonValue, as_integer, as_mapping, as_string
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.net.session_proof import proof_headers
from nostalgia.server.model import ServerAccess, ServerLease


class HttpServerGateway:
    def __init__(self, base_url: str, http_client: HttpClient, access_token: str) -> None:
        parts = urlsplit(base_url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise ServerError("Địa chỉ dịch vụ server phải dùng HTTPS.")
        if parts.path not in ("", "/") or parts.query or parts.fragment:
            raise ServerError("Địa chỉ dịch vụ server không hợp lệ.")
        self._base_url, self._http_client, self._token = (
            base_url.rstrip("/"),
            http_client,
            access_token,
        )

    def authorize(self) -> ServerAccess:
        document = self._request("GET", "/access")
        plan_name = as_string(document.get("plan_name")) or ""
        if document.get("server_hosting") is not True or plan_name not in (
            "Pro",
            "Max",
            "Ultimate",
        ):
            raise ServerError("Host server dành cho Pro, Max và Ultimate.")
        if document.get("hosting_mode") != "local" or document.get("maximum_running") != 1:
            raise ServerError("Cấu hình dịch vụ server không hợp lệ.")
        return ServerAccess(plan_name)

    def start(self, server_id: str) -> ServerLease:
        return self._lease(self._request("POST", "/start", {"server_id": server_id}), server_id)

    def renew(self, lease: ServerLease) -> ServerLease:
        return self._lease(self._request("POST", "/renew", self._document(lease)), lease.server_id)

    def release(self, lease: ServerLease) -> None:
        self._request("POST", "/stop", self._document(lease))

    def _document(self, lease: ServerLease) -> dict[str, JsonValue]:
        return {"server_id": lease.server_id, "lease_token": lease.lease_token}

    def _lease(self, document: dict[str, JsonValue], server_id: str) -> ServerLease:
        lease_token = as_string(document.get("lease_token")) or ""
        expires = as_integer(document.get("expires_at")) or 0
        if document.get("server_id") != server_id or not re.fullmatch(r"[a-f0-9]{64}", lease_token):
            raise ServerError("Không xác minh được phiên server.")
        if not time.time() < expires <= time.time() + 180:
            raise ServerError("Phiên server đã hết hạn hoặc sai thời hạn.")
        return ServerLease(server_id, lease_token, expires)

    def _request(self, method: str, path: str, document: JsonValue = None) -> dict[str, JsonValue]:
        if not self._token:
            raise SessionRevoked("Cần đăng nhập Google để dùng server.")
        payload = json.dumps(document).encode() if document is not None else None
        response = self._http_client.send(
            method,
            self._base_url + "/v1/servers" + path,
            headers={
                "Authorization": "Bearer " + self._token,
                "Content-Type": "application/json",
                **proof_headers(
                    self._token, method, self._base_url + "/v1/servers" + path, payload
                ),
            },
            body=payload,
            max_bytes=8192,
        )
        if response.status == 401:
            raise SessionRevoked("Phiên Google hết hạn hoặc đã đăng nhập trên máy khác.")
        if not response.is_ok:
            messages = {
                403: "Host server cần gói Pro, Max hoặc Ultimate đang hoạt động.",
                409: "Tài khoản đang có server chạy hoặc phiên server đã hết hạn.",
                503: "Host server trả phí đang tạm vô hiệu hoá.",
            }
            raise ServerError(
                messages.get(response.status, "Không xác nhận được quyền host server.")
            )
        return as_mapping(decode_json(response.body, what="quyền host server"))
