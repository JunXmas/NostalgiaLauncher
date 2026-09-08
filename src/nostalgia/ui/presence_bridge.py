"""Cầu nối Discord Rich Presence: bật thì khi game chạy, hồ sơ Discord hiện "Đang chơi
<bản chơi>" kèm thời gian chơi; game thoát thì xoá. Việc socket chạy ở luồng nền; trạng thái
về luồng giao diện qua tín hiệu xếp hàng.

Application ID do người dùng tự tạo ở Discord Developer Portal và dán vào CÀI ĐẶT — không
mã hoá cứng ID nào trong kho.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.discord_presence import DiscordPresence

type PresenceFactory = Callable[[str], DiscordPresence]
type SettingsFn = Callable[[], tuple[bool, str]]


class PresenceBridge(QObject):
    statusChanged = Signal()
    _statusArrived = Signal(bool, str)

    def __init__(
        self,
        bridge: LauncherBridge,
        *,
        read_settings: SettingsFn,
        instance_label: Callable[[str], str],
        make_presence: PresenceFactory = DiscordPresence,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._read_settings = read_settings
        self._instance_label = instance_label
        self._make_presence = make_presence
        self._presence: DiscordPresence | None = None
        self._lock = threading.Lock()
        self._connected = False
        self._status_text = "Chưa kết nối"
        self._statusArrived.connect(self._apply_status)
        bridge.gameStarted.connect(self._on_game_started)
        bridge.gameStopped.connect(self._on_game_stopped)

    @Property(bool, notify=statusChanged)
    def connected(self) -> bool:
        return self._connected

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    @Slot(str)
    def _on_game_started(self, instance_id: str) -> None:
        enabled, client_id = self._read_settings()
        if not enabled or not client_id.strip():
            return
        details = f"Đang chơi {self._instance_label(instance_id)}"
        started_at = int(time.time())
        threading.Thread(
            target=self._show, args=(client_id, details, started_at), daemon=True
        ).start()

    @Slot(int)
    def _on_game_stopped(self, _exit_code: int) -> None:
        threading.Thread(target=self._hide, daemon=True).start()

    def _show(self, client_id: str, details: str, started_at: int) -> None:
        with self._lock:
            if self._presence is None or not self._presence.connected:
                self._presence = self._make_presence(client_id)
                if not self._presence.connect():
                    self._presence = None
                    self._statusArrived.emit(False, "Không thấy Discord đang chạy")
                    return
            shown = self._presence.set_activity(details, "Nostalgia Launcher", started_at)
        self._statusArrived.emit(
            shown, "Đang hiện trên Discord" if shown else "Discord ngắt kết nối"
        )

    def _hide(self) -> None:
        with self._lock:
            if self._presence is not None:
                self._presence.clear_activity()
                self._presence.close()
                self._presence = None
        self._statusArrived.emit(False, "Đã xoá trạng thái")

    def shutdown(self) -> None:
        """Đóng launcher là xoá presence — không để Discord hiện "đang chơi" mãi."""
        self._hide()

    @Slot(bool, str)
    def _apply_status(self, connected: bool, text: str) -> None:
        self._connected = connected
        self._status_text = text
        self.statusChanged.emit()
