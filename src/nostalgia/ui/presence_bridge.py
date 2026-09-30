"""Cầu nối Discord Rich Presence: hồ sơ Discord hiện "Đang ở launcher" từ lúc mở launcher,
đổi sang "Đang chơi <bản chơi>" kèm thời gian chơi khi game chạy, và "Đang chơi chung" khi
đang ở phòng chơi chung. Việc socket chạy ở luồng nền; trạng thái về luồng giao diện qua tín
hiệu xếp hàng.

Application ID ghim sẵn trong kho (`repo/endpoints.py`) — người chơi không phải tạo app hay
dán id vào đâu cả. Discord mở sau launcher cũng được: hẹn giờ thử lại đều đặn, vì thất bại
một lần mà im mãi thì tính năng coi như không tồn tại với ai quen bật game trước.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from nostalgia.settings.store import discord_application_id
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.discord_presence import DiscordPresence

type PresenceFactory = Callable[[str], DiscordPresence]

IDLE_DETAILS = "Đang ở launcher"
RETRY_SECONDS = 30.0


class PresenceBridge(QObject):
    statusChanged = Signal()
    _statusArrived = Signal(bool, str)

    def __init__(
        self,
        bridge: LauncherBridge,
        *,
        is_enabled: Callable[[], bool],
        instance_label: Callable[[str], str],
        client_id: str | None = None,
        make_presence: PresenceFactory = DiscordPresence,
        retry_seconds: float = RETRY_SECONDS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._is_enabled = is_enabled
        self._instance_label = instance_label
        self._client_id = discord_application_id() if client_id is None else client_id
        self._make_presence = make_presence
        self._presence: DiscordPresence | None = None
        self._lock = threading.Lock()
        self._busy = False
        self._connected = False
        self._status_text = "Chưa kết nối"
        self._room_state = "Nostalgia Launcher"
        self._details = IDLE_DETAILS
        self._started_at = int(time.time())
        self._statusArrived.connect(self._apply_status)
        bridge.gameStarted.connect(self._on_game_started)
        bridge.gameStopped.connect(self._on_game_stopped)
        self._timer = QTimer(self)
        self._timer.setInterval(max(1, int(retry_seconds * 1000)))
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._push()

    @Property(bool, notify=statusChanged)
    def connected(self) -> bool:
        return self._connected

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @Slot(str)
    def _on_game_started(self, instance_id: str) -> None:
        self._details = f"Đang chơi {self._instance_label(instance_id)}"
        self._started_at = int(time.time())
        self._push()

    @Slot(int)
    def _on_game_stopped(self, _exit_code: int) -> None:
        """Game thoát KHÔNG phải là hết chuyện: người chơi vẫn đang ở launcher, nên quay về
        trạng thái nghỉ chứ không xoá sạch."""
        self._details = IDLE_DETAILS
        self._started_at = int(time.time())
        self._push()

    def setRoomState(self, role: str, joiner_count: int) -> None:
        """Gọi khi `MultiplayerBridge` đổi trạng thái phòng. KHÔNG đưa mã phòng vào presence
        — mã phòng là bí mật vào phòng, phát công khai lên Discord là mời người lạ vào nhà."""
        self._room_state = self._describe_room(role, joiner_count)
        self._push()

    @staticmethod
    def _describe_room(role: str, joiner_count: int) -> str:
        if role == "hosting" and joiner_count > 0:
            plural = "người" if joiner_count == 1 else f"{joiner_count} người"
            return f"Đang chơi chung với {plural}"
        if role in ("hosting", "joined"):
            return "Đang chơi chung"
        return "Nostalgia Launcher"

    @Slot()
    def _tick(self) -> None:
        """Nhịp hẹn giờ: nối lại khi Discord mới mở, và gỡ presence khi người dùng vừa gạt
        công tắc trong CÀI ĐẶT (không cần nối tín hiệu riêng cho công tắc)."""
        if not self._is_enabled():
            if self._connected:
                threading.Thread(target=self._hide, daemon=True).start()
            return
        if not self._connected and not self._busy:
            self._push()

    def _push(self) -> None:
        if not self._is_enabled():
            return
        threading.Thread(
            target=self._show,
            args=(self._details, self._room_state, self._started_at),
            daemon=True,
        ).start()

    def _show(self, details: str, state: str, started_at: int) -> None:
        self._busy = True
        try:
            with self._lock:
                if self._presence is None or not self._presence.connected:
                    self._presence = self._make_presence(self._client_id)
                    if not self._presence.connect():
                        self._presence = None
                        self._statusArrived.emit(False, "Không thấy Discord đang chạy")
                        return
                shown = self._presence.set_activity(details, state, started_at)
            self._statusArrived.emit(
                shown, "Đang hiện trên Discord" if shown else "Discord ngắt kết nối"
            )
        finally:
            self._busy = False

    def _hide(self) -> None:
        with self._lock:
            if self._presence is not None:
                self._presence.clear_activity()
                self._presence.close()
                self._presence = None
        self._statusArrived.emit(False, "Đã xoá trạng thái")

    def shutdown(self) -> None:
        """Đóng launcher là xoá presence — không để Discord hiện "đang chơi" mãi."""
        self._timer.stop()
        self._hide()

    @Slot(bool, str)
    def _apply_status(self, connected: bool, text: str) -> None:
        self._connected = connected
        self._status_text = text
        self.statusChanged.emit()
