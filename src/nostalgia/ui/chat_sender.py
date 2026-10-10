"""Gửi chat độc lập với polling; bỏ kết quả khi phiên đã đổi hoặc bị thu hồi."""

from __future__ import annotations

import uuid

from PySide6.QtCore import Signal, Slot

from nostalgia.api import SocialGateway
from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.ui.worker import WorkerBridge


class ChatSender(WorkerBridge):
    completed = Signal(str, str, str, bool)
    _arrived = Signal(int, str, str, str, bool, str)

    def __init__(self, parent: WorkerBridge) -> None:
        super().__init__(parent)
        self._gateway: SocialGateway | None = None
        self._arrived.connect(self._apply)

    def submit(self, gateway: SocialGateway, peer_id: str, text: str) -> None:
        if self.busy:
            return
        self._gateway = gateway
        access_token = gateway.access_token
        generation = self.next_generation()
        message_id = uuid.uuid4().hex

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
            self._arrived.emit(generation, peer_id, text, error, revoked, access_token)

        self.run_in_background(send, "Đang gửi tin nhắn…")

    def cancel(self) -> None:
        self.next_generation()

    @Slot(int, str, str, str, bool, str)
    def _apply(
        self,
        generation: int,
        peer_id: str,
        text: str,
        error: str,
        revoked: bool,
        access_token: str,
    ) -> None:
        if (
            self.is_current(generation)
            and self._gateway
            and self._gateway.access_token == access_token
        ):
            self.completed.emit(peer_id, text, error, revoked)
