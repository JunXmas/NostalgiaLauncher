"""Hàng đợi gửi chat tuần tự, độc lập với polling; bỏ kết quả khi phiên đã đổi hoặc bị thu hồi."""

from __future__ import annotations

import uuid

from PySide6.QtCore import Signal, Slot

from nostalgia.api import SocialGateway
from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.ui.worker import WorkerBridge


class ChatSender(WorkerBridge):
    completed = Signal(str, str, bool)
    _arrived = Signal(int, str, str, bool, str)

    def __init__(self, parent: WorkerBridge) -> None:
        super().__init__(parent)
        self._gateway: SocialGateway | None = None
        self._outbox: list[tuple[str, str, str]] = []
        self._arrived.connect(self._apply)
        self.busyChanged.connect(self._send_next)

    def submit(self, gateway: SocialGateway, peer_id: str, text: str, message_id: str = "") -> str:
        """Xếp tin vào hàng đợi; gửi lại dùng lại `message_id` để máy chủ không nhân đôi."""
        message_id = message_id or uuid.uuid4().hex
        self._gateway = gateway
        self._outbox.append((peer_id, text, message_id))
        self._send_next()
        return message_id

    @Slot()
    def _send_next(self) -> None:
        gateway = self._gateway
        if self.busy or not self._outbox or gateway is None:
            return
        peer_id, text, message_id = self._outbox[0]
        access_token = gateway.access_token
        generation = self.next_generation()

        def send() -> None:
            error, revoked = "", False
            try:
                if gateway.access_token != access_token:
                    return
                gateway.send_message(peer_id, text, message_id)
            except SessionRevoked as exc:
                error, revoked = str(exc), True
            except SocialError as exc:
                error = str(exc)
            except Exception:
                error = "Không gửi được tin nhắn. Hãy thử lại."
            self._arrived.emit(generation, message_id, error, revoked, access_token)

        self.run_in_background(send, "Đang gửi tin nhắn…")

    def cancel(self) -> None:
        self._outbox.clear()
        self.next_generation()

    @Slot(int, str, str, bool, str)
    def _apply(
        self, generation: int, message_id: str, error: str, revoked: bool, access_token: str
    ) -> None:
        if (
            self.is_current(generation)
            and self._gateway
            and self._gateway.access_token == access_token
        ):
            self._outbox = [queued for queued in self._outbox if queued[2] != message_id]
            self.completed.emit(message_id, error, revoked)
