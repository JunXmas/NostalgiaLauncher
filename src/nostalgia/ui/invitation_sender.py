"""Lời mời chạy riêng khỏi polling; bỏ kết quả của tài khoản cũ."""

from collections.abc import Callable

from PySide6.QtCore import Signal, Slot

from nostalgia.api import SocialGateway
from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.ui.worker import WorkerBridge


class InvitationSender(WorkerBridge):
    completed = Signal(str, str, bool)
    _arrived = Signal(int, str, str, bool, str)

    def __init__(self, parent: WorkerBridge) -> None:
        super().__init__(parent)
        self._gateway: SocialGateway | None = None
        self._arrived.connect(self._apply)

    def submit(self, gateway: SocialGateway, work: Callable[[], str]) -> None:
        if self.busy:
            return
        self._gateway = gateway
        access_token = gateway.access_token
        generation = self.next_generation()

        def send() -> None:
            room_code, error, revoked = "", "", False
            try:
                if gateway.access_token != access_token:
                    return
                room_code = work()
            except SessionRevoked as exc:
                error, revoked = str(exc), True
            except SocialError as exc:
                error = str(exc)
            except Exception:
                error = "Không kết nối được dịch vụ. Hãy thử lại."
            self._arrived.emit(generation, room_code, error, revoked, access_token)

        self.run_in_background(send, "Đang xử lý...")

    def cancel(self) -> None:
        self.next_generation()

    @Slot(int, str, str, bool, str)
    def _apply(
        self, generation: int, room_code: str, error: str, revoked: bool, access_token: str
    ) -> None:
        if (
            self.is_current(generation)
            and self._gateway
            and self._gateway.access_token == access_token
        ):
            self.completed.emit(room_code, error, revoked)
