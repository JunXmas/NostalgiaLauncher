"""Local review permission for real server operations, never a server-issued lease."""

from __future__ import annotations

import secrets
import threading
import time

from nostalgia.errors import ServerError
from nostalgia.server.model import ServerAccess, ServerLease
from nostalgia_draft.social import ReviewSocial


class ReviewServer:
    def __init__(self, social: ReviewSocial) -> None:
        self._social = social
        self._lease: ServerLease | None = None
        self._lock = threading.Lock()

    def authorize(self) -> ServerAccess:
        name = {
            "plus-half-year-v1": "Pro",
            "plus-year-v2": "Max",
            "plus-lifetime-v1": "Ultimate",
        }.get(self._social.snapshot.account.plus_plan)
        if not name or not self._social.access_token:
            raise ServerError("Chọn Pro, Max hoặc Ultimate trong Công cụ Draft để thử host server.")
        return ServerAccess(name)

    def start(self, server_id: str) -> ServerLease:
        self.authorize()
        with self._lock:
            if self._lease and self._lease.expires_at > time.time():
                raise ServerError("Bản TEST chỉ chạy một server tại một thời điểm.")
            self._lease = ServerLease(server_id, secrets.token_hex(32), int(time.time()) + 120)
            return self._lease

    def renew(self, lease: ServerLease) -> ServerLease:
        self.authorize()
        with self._lock:
            if self._lease != lease or lease.expires_at <= time.time():
                raise ServerError("Phiên server TEST đã kết thúc.")
            self._lease = ServerLease(lease.server_id, lease.lease_token, int(time.time()) + 120)
            return self._lease

    def release(self, lease: ServerLease) -> None:
        with self._lock:
            if self._lease == lease:
                self._lease = None
