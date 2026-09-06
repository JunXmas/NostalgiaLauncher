"""Cầu nối trang CÀI ĐẶT: khoá API CurseForge (tuỳ chọn) của người dùng.

Khoá chỉ nằm trong settings.json (0600) hoặc biến môi trường; QML không cần biết khoá thật,
chỉ cần biết đã có hay chưa để hiện đúng trạng thái.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.settings.store import CURSEFORGE_KEY_ENV
from nostalgia.ui.worker import WorkerBridge


class SettingsBridge(WorkerBridge):
    settingsChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher

    @Property(bool, notify=settingsChanged)
    def hasCurseforgeKey(self) -> bool:
        return self._launcher.load_settings().has_curseforge_key

    @Property(str, constant=True)
    def curseforgeKeyEnvName(self) -> str:
        return CURSEFORGE_KEY_ENV

    @Slot(str)
    def saveCurseforgeKey(self, api_key: str) -> None:
        """Ghi khoá (rỗng = xoá). Đọc/ghi một file nhỏ nên làm ngay, không cần luồng nền."""
        settings = replace(self._launcher.load_settings(), curseforge_api_key=api_key.strip())
        self._launcher.save_settings(settings)
        self.settingsChanged.emit()
