"""Cầu nối trang CÀI ĐẶT: thông tin chung của launcher (phiên bản, thư mục dữ liệu).

Khoá API CurseForge KHÔNG còn nhập ở đây: thư viện đi qua máy chủ của dự án, ai muốn dùng
khoá riêng thì đặt biến môi trường (xem `settings/store.py`).
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, QUrl, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia import __version__
from nostalgia.api import Launcher


class SettingsBridge(QObject):
    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher

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
