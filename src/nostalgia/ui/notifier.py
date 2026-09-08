"""Thông báo sự kiện khởi chạy: toast trên màn hình + chuông (nếu bật trong CÀI ĐẶT).

Nghe tín hiệu của cầu nối chính (game khởi động / thoát / cài xong phiên bản) rồi phát ra
MỘT tín hiệu `notified(eventKind, title, detail)` cho QML vẽ toast. Tín hiệu gốc tới từ luồng
nền; các slot ở đây chạy trên luồng giao diện nhờ kết nối queued của Qt.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.sound import SoundPlayer

type LabelFn = Callable[[str], str]
type EnabledFn = Callable[[], bool]


class Notifier(QObject):
    notified = Signal(str, str, str)

    def __init__(
        self,
        bridge: LauncherBridge,
        *,
        player: SoundPlayer,
        sound_enabled: EnabledFn,
        instance_label: LabelFn,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._player = player
        self._sound_enabled = sound_enabled
        self._instance_label = instance_label
        bridge.gameStarted.connect(self._on_game_started)
        bridge.gameStopped.connect(self._on_game_stopped)
        bridge.versionInstalled.connect(self._on_version_installed)

    def announce(self, event_kind: str, title: str, detail: str) -> None:
        self.notified.emit(event_kind, title, detail)
        if self._sound_enabled():
            self._player.play(event_kind)

    @Slot(str)
    def _on_game_started(self, instance_id: str) -> None:
        self.announce("started", "Game đã khởi động", self._instance_label(instance_id))

    @Slot(int)
    def _on_game_stopped(self, exit_code: int) -> None:
        if exit_code == 0:
            self.announce("stopped", "Game đã thoát", "Hẹn gặp lại!")
        else:
            self.announce("crashed", "Game gặp sự cố", f"Mã thoát {exit_code} — xem NHẬT KÝ")

    @Slot(str)
    def _on_version_installed(self, version_id: str) -> None:
        self.announce("installed", "Đã tải xong", f"Minecraft {version_id} sẵn sàng")
