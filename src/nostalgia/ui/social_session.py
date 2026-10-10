"""Đăng nhập trình duyệt và kiểm phiên trên máy chủ, không cấp Plus bằng cờ Qt."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import (
    GoogleLogin,
    ServiceSessionStore,
    SocialGateway,
    SocialSnapshot,
    SocialUpdate,
)
from nostalgia.errors import SessionRevoked, SocialError
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.social_state import SocialState


class SocialSession(SocialState):
    _arrived = Signal(int, str, object, str)

    def __init__(
        self,
        gateway: SocialGateway | None,
        multiplayer: MultiplayerBridge,
        sync_bridge: RoomSyncBridge,
        parent: QObject | None = None,
        session_store: ServiceSessionStore | None = None,
        plus_enabled: bool = True,
    ) -> None:
        super().__init__(parent)
        self._gateway = gateway
        self._plus_enabled = plus_enabled
        self._session_store = session_store
        self._multiplayer = multiplayer
        self._sync_bridge = sync_bridge
        self._snapshot: SocialSnapshot | None = None
        self._last_update: SocialUpdate | None = None
        self._messages = []
        self._peer_id = ""
        self._login: GoogleLogin | None = None
        self._note = ""
        self._refresh_pending = False
        self._watching = False
        self._arrived.connect(self._apply)
        self.busyChanged.connect(self._flush_refresh)
        self._timer = QTimer(self)
        self._timer.setInterval(15000)
        self._timer.timeout.connect(self.refresh)
        self._login_timer = QTimer(self)
        self._login_timer.setInterval(3000)
        self._login_timer.timeout.connect(self._poll_login)

    @Slot()
    def restoreSession(self) -> None:
        if self._session_store and not self.busy and not self.access_token():
            self._request("signed", self._session_store.load_access_token)

    @Slot()
    def signIn(self) -> None:
        if self._gateway is None or self.busy or self._login or self.signedIn:
            return
        self._request("start", self._gateway.start_login)

    @Slot()
    def cancelSignIn(self) -> None:
        self.next_generation()
        self._login_timer.stop()
        self._login = None
        self._note = ""
        self.changed.emit()

    @Slot()
    def openGoogle(self) -> None:
        if self._login and not QDesktopServices.openUrl(QUrl(self._login.authorization_url)):
            self._note = (
                "Không mở được trình duyệt. Hãy kiểm tra trình duyệt mặc định "
                "rồi bấm Mở lại Google."
            )
            self.changed.emit()

    @Slot()
    def signOut(self) -> None:
        if self.busy or self._gateway is None or not self.signedIn:
            return
        # Chỉ báo đăng xuất thành công sau khi server thu hồi phiên.
        self._request("logout", self._gateway.logout)

    @Slot()
    def shutdown(self) -> None:
        self.next_generation()
        self._refresh_pending = False
        self._timer.stop()
        self._login_timer.stop()
        if self._gateway:
            self._gateway.access_token = ""

    @Slot()
    def refresh(self) -> None:
        gateway, peer_id = self._gateway, self._peer_id
        watching, cached_messages = self._watching, self.resolve_cached_messages(peer_id)
        if gateway is None or not gateway.access_token:
            return
        if self.busy:
            self._refresh_pending = True
            return
        self._refresh_pending = False

        def fetch() -> SocialUpdate:
            snapshot = gateway.fetch_snapshot()
            messages = (
                (gateway.fetch_messages(peer_id) if watching else cached_messages)
                if any(friend.account_id == peer_id for friend in snapshot.friends)
                else ()
            )
            return SocialUpdate(snapshot, messages, peer_id)

        self._request("update", fetch)

    @Slot()
    def _flush_refresh(self) -> None:
        if self._refresh_pending and not self.busy:
            QTimer.singleShot(0, self.refresh)

    @Slot()
    def _poll_login(self) -> None:
        gateway, login = self._gateway, self._login
        if login is None or gateway is None or self.busy:
            return
        if login.expires_at <= time.time():
            self.cancelSignIn()
            self._note = "Đăng nhập đã hết thời gian. Hãy thử lại."
            self.changed.emit()
            return
        self._request("signed", lambda: gateway.poll_login(login))

    def _request(self, operation: str, work: Callable[[], object]) -> None:
        generation = self.next_generation()

        def perform() -> None:
            try:
                payload = work()
                if self._session_store and self.is_current(generation):
                    if operation == "signed" and isinstance(payload, str) and payload:
                        self._session_store.save_access_token(payload)
                    elif operation == "logout":
                        self._session_store.remove_access_token()
            except SessionRevoked as exc:
                if self._session_store:
                    self._session_store.remove_access_token()
                self._arrived.emit(generation, "revoked", None, str(exc))
            except SocialError as exc:
                self._arrived.emit(generation, "error", None, str(exc))
            except Exception:
                self._arrived.emit(
                    generation, "error", None, "Không kết nối được dịch vụ. Hãy thử lại."
                )
            else:
                self._arrived.emit(generation, operation, payload, "")

        self.run_in_background(perform, "Đang đồng bộ tài khoản Nostalgia…")

    @Slot(int, str, object, str)
    def _apply(self, generation: int, operation: str, payload: object, error: str) -> None:
        if not self.is_current(generation):
            return
        if operation in ("logout", "revoked"):
            self._reset_session(error or "Đã đăng xuất.")
        elif error:
            self._note = error
            if self._login:
                self.cancelSignIn()
                self._note = error
        elif operation == "start" and isinstance(payload, GoogleLogin):
            self._login = payload
            self._login_timer.start()
            self._note = "Hoàn tất đăng nhập Google trong trình duyệt để quay lại launcher."
            self.openGoogle()
        elif operation == "signed" and isinstance(payload, str) and payload and self._gateway:
            self._gateway.access_token = payload
            self._login_timer.stop()
            self._login = None
            self._timer.start()
            self.sessionChanged.emit()
            QTimer.singleShot(30, self.refresh)
        elif isinstance(payload, SocialUpdate):
            if payload == self._last_update and payload.peer_id == self._peer_id and not self._note:
                return
            self._last_update = payload
            self._snapshot = payload.snapshot
            self.update_messages(payload)
            if not any(friend.account_id == self._peer_id for friend in payload.snapshot.friends):
                self._peer_id, self._messages = "", []
            self._note = ""
            if payload.peer_id != self._peer_id and self._peer_id:
                QTimer.singleShot(30, self.refresh)
        elif operation == "join" and isinstance(payload, str):
            self._sync_bridge.join(payload)
            self._note = "Đang vào phòng của bạn…"
            QTimer.singleShot(30, self.refresh)
        elif operation == "preview" and isinstance(payload, str):
            QDesktopServices.openUrl(QUrl(payload))
            self._note = "Đã mở bản thử nghiệm riêng cho gói của bạn."
        elif operation == "changed":
            self._note = "Đã gửi."
            QTimer.singleShot(30, self.refresh)
        self.changed.emit()

    def _reset_session(self, note: str) -> None:
        self.next_generation()
        self._refresh_pending = False
        self._timer.stop()
        self._login_timer.stop()
        self._login = self._snapshot = self._last_update = None
        self._messages, self._peer_id, self._note = [], "", note
        if self._gateway:
            self._gateway.access_token = ""
        self._multiplayer.stop()
        self._sync_bridge.cancel()
        self.sessionChanged.emit()
