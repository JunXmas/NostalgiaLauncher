"""Thao tác kết bạn độc lập với polling; không áp kết quả của phiên cũ."""

from __future__ import annotations

from PySide6.QtCore import Signal, Slot

from nostalgia.api import SocialGateway
from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.ui.worker import WorkerBridge


class FriendSender(WorkerBridge):
    completed = Signal(str, bool)
    _arrived = Signal(int, str, bool, str)

    def __init__(self, parent: WorkerBridge) -> None:
        super().__init__(parent)
        self._gateway: SocialGateway | None = None
        self._arrived.connect(self._apply)

    def submit(self, gateway: SocialGateway, action: str, account_id: str) -> None:
        if self.busy:
            return
        self._gateway = gateway
        access_token = gateway.access_token
        generation = self.next_generation()

        def send() -> None:
            error, revoked = "", False
            try:
                if gateway.access_token != access_token:
                    return
                gateway.friend_action(action, account_id)
            except SessionRevoked as exc:
                error, revoked = str(exc), True
            except SocialError as exc:
                error = str(exc)
            except Exception:
                error = "Không kết nối được dịch vụ. Hãy thử lại."
            self._arrived.emit(generation, error, revoked, access_token)

        self.run_in_background(send, "Đang xử lý...")

    def cancel(self) -> None:
        self.next_generation()

    @Slot(int, str, bool, str)
    def _apply(self, generation: int, error: str, revoked: bool, access_token: str) -> None:
        if (
            self.is_current(generation)
            and self._gateway
            and self._gateway.access_token == access_token
        ):
            self.completed.emit(error, revoked)
