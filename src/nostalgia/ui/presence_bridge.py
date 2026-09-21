"""Cầu nối Discord Rich Presence: bật thì khi game chạy, hồ sơ Discord hiện "Đang chơi
<bản chơi>" kèm thời gian chơi; đang ở phòng chơi chung thì đổi sang "Đang chơi chung"; game
thoát thì xoá. Việc socket chạy ở luồng nền; trạng thái về luồng giao diện qua tín hiệu xếp
hàng.

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
        self._room_state = "Nostalgia Launcher"
        # (client_id, details, started_at) trong khi presence đang hiện; None nghĩa là game
        # không chạy — không có gì để nhắc trạng thái phòng vào.
        self._active: tuple[str, str, int] | None = None
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
        self._active = (client_id, details, started_at)
        threading.Thread(
            target=self._show, args=(client_id, details, started_at), daemon=True
        ).start()

    @Slot(int)
    def _on_game_stopped(self, _exit_code: int) -> None:
        self._active = None
        threading.Thread(target=self._hide, daemon=True).start()

    def setRoomState(self, role: str, joiner_count: int) -> None:
        """Gọi khi `MultiplayerBridge` đổi trạng thái phòng. KHÔNG đưa mã phòng vào presence
        — mã phòng là bí mật vào phòng, phát công khai lên Discord là mời người lạ vào nhà."""
        self._room_state = self._describe_room(role, joiner_count)
        if self._active is not None:
            client_id, details, started_at = self._active
            threading.Thread(
                target=self._show, args=(client_id, details, started_at), daemon=True
            ).start()

    @staticmethod
    def _describe_room(role: str, joiner_count: int) -> str:
        if role == "hosting" and joiner_count > 0:
            plural = "người" if joiner_count == 1 else f"{joiner_count} người"
            return f"Đang chơi chung với {plural}"
        if role in ("hosting", "joined"):
            return "Đang chơi chung"
        return "Nostalgia Launcher"

    def _show(self, client_id: str, details: str, started_at: int) -> None:
        with self._lock:
            if self._presence is None or not self._presence.connected:
                self._presence = self._make_presence(client_id)
                if not self._presence.connect():
                    self._presence = None
                    self._statusArrived.emit(False, "Không thấy Discord đang chạy")
                    return
            shown = self._presence.set_activity(details, self._room_state, started_at)
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
