"""Phần "đã cài" của cầu nối nội dung: liệt kê file trong thư mục bản chơi, bật/tắt, gỡ.

Tách khỏi `content_bridge.py` cho mỗi file ngắn; cùng một QObject nhìn từ QML.
"""

from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.model import ContentKind
from nostalgia.ui.worker import WorkerBridge


class InstalledContentBridge(WorkerBridge):
    installedChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._target: ContentTarget | None = None
        self._installed: list[dict[str, Any]] = []

    @Property(list, notify=installedChanged)
    def installed(self) -> list[dict[str, Any]]:
        return self._installed

    @Slot(str)
    def refreshInstalled(self, content_kind: str) -> None:
        """Đọc đĩa, không chạm mạng — làm ngay, không cần luồng nền."""
        self._reload_installed(cast(ContentKind, content_kind))

    @Slot(str, str, bool)
    def setEnabled(self, content_kind: str, file_name: str, enabled: bool) -> None:
        if self._target is None:
            return
        chosen_kind = cast(ContentKind, content_kind)
        self._launcher.set_content_enabled(self._target, chosen_kind, file_name, enabled)
        self._reload_installed(chosen_kind)

    @Slot(str, str)
    def remove(self, content_kind: str, file_name: str) -> None:
        if self._target is None:
            return
        chosen_kind = cast(ContentKind, content_kind)
        self._launcher.remove_content(self._target, chosen_kind, file_name)
        self._reload_installed(chosen_kind)

    def _reload_installed(self, content_kind: ContentKind) -> None:
        if self._target is None:
            return
        self._installed = [
            {
                "fileName": installed.file_name,
                "label": installed.label,
                "fileSize": installed.file_size,
                "enabled": installed.enabled,
                "projectId": installed.project_id,
                "versionNumber": installed.version_number,
                "contentKind": installed.content_kind,
            }
            for installed in self._launcher.list_installed_content(self._target, content_kind)
        ]
        self.installedChanged.emit()
