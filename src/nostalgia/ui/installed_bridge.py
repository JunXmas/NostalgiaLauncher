"""Phần "đã cài" của cầu nối nội dung: liệt kê file trong thư mục bản chơi, bật/tắt, gỡ.

Tách khỏi `content_bridge.py` cho mỗi file ngắn; cùng một QObject nhìn từ QML.
"""

from __future__ import annotations

from typing import Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.model import ContentKind
from nostalgia.ui.row_model import KeyedRowModel
from nostalgia.ui.worker import WorkerBridge

INSTALLED_ROLES = (
    "fileName",
    "label",
    "fileSize",
    "enabled",
    "projectId",
    "versionNumber",
    "contentKind",
    "iconUrl",
)


class InstalledContentBridge(WorkerBridge):
    installedChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._target: ContentTarget | None = None
        self._installed_model = KeyedRowModel(INSTALLED_ROLES, key="fileName", parent=self)
        self._installed_rows: list[dict[str, Any]] = []
        self._installed_filter = ""

    @Property(QObject, constant=True)
    def installedModel(self) -> KeyedRowModel:
        """Mô hình cho ListView: đồng bộ tối thiểu, không reset, giữ vị trí cuộn."""
        return self._installed_model

    @Property(list, notify=installedChanged)
    def installed(self) -> list[dict[str, Any]]:
        """Toàn bộ, chưa lọc; mô hình chỉ giữ phần khớp ô tìm."""
        return list(self._installed_rows)

    @Property(int, notify=installedChanged)
    def installedShownCount(self) -> int:
        """Số mục khớp ô tìm (rowCount của mô hình không tự báo đổi cho binding QML)."""
        return self._installed_model.rowCount()

    @Slot(str)
    def setInstalledFilter(self, text: str) -> None:
        """Lọc theo tên hoặc tên file, ngay trên mô hình — giữ vị trí cuộn, không dựng lại."""
        self._installed_filter = text.strip().lower()
        self._sync_installed_model()
        self.installedChanged.emit()

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
        rows: list[dict[str, Any]] = [
            {
                "fileName": installed.file_name,
                "label": installed.label,
                "fileSize": installed.file_size,
                "enabled": installed.enabled,
                "projectId": installed.project_id,
                "versionNumber": installed.version_number,
                "contentKind": installed.content_kind,
                "iconUrl": installed.icon_url,
            }
            for installed in self._launcher.list_installed_content(self._target, content_kind)
        ]
        self._installed_rows = rows
        self._sync_installed_model()
        self.installedChanged.emit()

    def _sync_installed_model(self) -> None:
        needle = self._installed_filter
        self._installed_model.sync(
            [
                row
                for row in self._installed_rows
                if not needle
                or needle in str(row["label"]).lower()
                or needle in str(row["fileName"]).lower()
            ]
        )
