"""Thiết lập endpoint cho bản draft mà không yêu cầu người thử paste khóa bí mật."""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher, ServiceConfiguration
from nostalgia.errors import NostalgiaError
from nostalgia.ui.worker import WorkerBridge


class ServiceConfigurationBridge(WorkerBridge):
    changed = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._configuration = launcher.load_service_configuration()
        self._note = ""

    @Property(str, notify=changed)
    def accountUrl(self) -> str:
        return self._configuration.account_url

    @Property(str, notify=changed)
    def roomSyncUrl(self) -> str:
        return self._configuration.room_sync_url

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    @Slot(str, str)
    def save(self, account_url: str, room_sync_url: str) -> None:
        try:
            self._launcher.save_service_configuration(
                ServiceConfiguration(account_url.strip(), room_sync_url.strip())
            )
            self._configuration = self._launcher.load_service_configuration()
            self._note = "Đã lưu. Khởi động lại launcher để nối dịch vụ mới."
        except NostalgiaError as error:
            self._note = str(error)
        self.changed.emit()
