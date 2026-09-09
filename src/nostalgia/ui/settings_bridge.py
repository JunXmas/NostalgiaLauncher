"""Cầu nối trang CÀI ĐẶT: thông tin chung của launcher (phiên bản, thư mục dữ liệu), công tắc
âm thanh thông báo và Discord Rich Presence.

Cấu hình đọc từ đĩa MỘT lần rồi giữ trong RAM; chỉ đọc lại sau khi chính cầu nối này ghi.
Trước đây mỗi binding QML và mỗi sự kiện game đều đọc + parse settings.json.

Khoá API CurseForge KHÔNG còn nhập ở đây: thư viện đi qua máy chủ của dự án, ai muốn dùng
khoá riêng thì đặt biến môi trường (xem `settings/store.py`).
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia import __version__
from nostalgia.api import Launcher, Settings


class SettingsBridge(QObject):
    notificationSoundChanged = Signal()
    uiSoundChanged = Signal()
    discordChanged = Signal()
    autoUpdateCheckChanged = Signal()
    gameDirRootChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._settings: Settings | None = None

    def settings_snapshot(self) -> Settings:
        if self._settings is None:
            self._settings = self._launcher.load_settings()
        return self._settings

    def _save(self, wanted: Settings) -> None:
        self._launcher.save_settings(wanted)
        self._settings = wanted

    @Property(bool, notify=notificationSoundChanged)
    def notificationSound(self) -> bool:
        return self.settings_snapshot().notification_sound

    @Property(bool, notify=uiSoundChanged)
    def uiSound(self) -> bool:
        return self.settings_snapshot().ui_sound

    @Property(bool, notify=discordChanged)
    def discordPresence(self) -> bool:
        return self.settings_snapshot().discord_presence

    @Property(str, notify=discordChanged)
    def discordApplicationId(self) -> str:
        return self.settings_snapshot().discord_application_id

    @Slot(bool, str)
    def setDiscord(self, enabled: bool, application_id: str) -> None:
        settings = self.settings_snapshot()
        wanted = replace(
            settings, discord_presence=enabled, discord_application_id=application_id.strip()
        )
        if wanted != settings:
            self._save(wanted)
            self.discordChanged.emit()

    @Property(str, notify=gameDirRootChanged)
    def defaultGameDirRoot(self) -> str:
        return self.settings_snapshot().default_game_dir_root

    @Slot(str)
    def setDefaultGameDirRoot(self, text: str) -> None:
        """Nhận đường dẫn hoặc URL file:// từ FolderDialog; rỗng = về mặc định."""
        chosen = QUrl(text).toLocalFile() if text.startswith("file:") else text
        chosen = self._launcher.check_game_dir(chosen)
        settings = self.settings_snapshot()
        if settings.default_game_dir_root != chosen:
            self._save(replace(settings, default_game_dir_root=chosen))
            self.gameDirRootChanged.emit()

    @Property(bool, notify=autoUpdateCheckChanged)
    def autoUpdateCheck(self) -> bool:
        return self.settings_snapshot().auto_update_check

    @Slot(bool)
    def setAutoUpdateCheck(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.auto_update_check != enabled:
            self._save(replace(settings, auto_update_check=enabled))
            self.autoUpdateCheckChanged.emit()

    @Slot(bool)
    def setNotificationSound(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.notification_sound != enabled:
            self._save(replace(settings, notification_sound=enabled))
            self.notificationSoundChanged.emit()

    @Slot(bool)
    def setUiSound(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.ui_sound != enabled:
            self._save(replace(settings, ui_sound=enabled))
            self.uiSoundChanged.emit()

    @Property(str, constant=True)
    def launcherVersion(self) -> str:
        return __version__

    @Property(str, constant=True)
    def dataDir(self) -> str:
        return str(self._launcher.paths.data_dir)

    @Slot()
    def openDataFolder(self) -> None:
        """Mở thư mục dữ liệu (versions/libraries/assets/instances) bằng trình quản lý file."""
        folder = self._launcher.paths.data_dir
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
