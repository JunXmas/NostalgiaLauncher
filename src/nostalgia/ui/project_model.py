"""Mô hình danh sách kết quả tìm kiếm cho GridView/ListView.

Vì sao không đưa thẳng mảng JS: mỗi lần gán mảng mới, view dựng lại toàn bộ delegate và
nhảy về đầu — bấm "Tải thêm" mà mất chỗ đang xem. Mô hình này nối thêm hàng (`append`) và
chỉ báo đổi ở hàng có cờ đổi, nên vị trí cuộn được giữ.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)

from nostalgia.content.model import Project

ROLE_NAMES = (
    "projectId",
    "title",
    "author",
    "description",
    "iconUrl",
    "downloads",
    "follows",
    "loaders",
    "installed",
    "installing",
    "contentKind",
    "source",
)
FIRST_ROLE = Qt.ItemDataRole.UserRole + 1


class ProjectListModel(QAbstractListModel):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._projects: list[Project] = []
        self._installed_ids: set[str] = set()
        self._installing_ids: set[str] = set()

    # ----- QAbstractListModel -----

    def rowCount(self, _parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._projects)

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            FIRST_ROLE + offset: QByteArray(name.encode()) for offset, name in enumerate(ROLE_NAMES)
        }

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = FIRST_ROLE) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._projects):
            return None
        return self.row(index.row())[ROLE_NAMES[role - FIRST_ROLE]]

    # ----- dùng từ cầu nối -----

    @property
    def projects(self) -> list[Project]:
        return list(self._projects)

    def row(self, position: int) -> dict[str, Any]:
        project = self._projects[position]
        return {
            "projectId": project.project_id,
            "title": project.title,
            "author": project.author,
            "description": project.description,
            "iconUrl": project.icon_url,
            "downloads": project.downloads,
            "follows": project.follows,
            "loaders": list(project.loaders),
            "installed": project.project_id in self._installed_ids,
            "installing": project.project_id in self._installing_ids,
            "contentKind": project.content_kind,
            "source": project.source,
        }

    def reset(self, projects: list[Project]) -> None:
        self.beginResetModel()
        self._projects = list(projects)
        self.endResetModel()

    def append(self, projects: list[Project]) -> None:
        """Nối thêm, bỏ những dự án đã có (Modrinth có thể trả trùng giữa hai trang)."""
        known = {project.project_id for project in self._projects}
        fresh = [project for project in projects if project.project_id not in known]
        if not fresh:
            return
        first = len(self._projects)
        self.beginInsertRows(QModelIndex(), first, first + len(fresh) - 1)
        self._projects.extend(fresh)
        self.endInsertRows()

    def set_flags(self, installed_ids: set[str], installing_ids: set[str]) -> None:
        """Đổi cờ đã cài / đang cài; chỉ báo những hàng mà cờ thật sự đổi."""
        changed = (self._installed_ids ^ installed_ids) | (self._installing_ids ^ installing_ids)
        self._installed_ids, self._installing_ids = set(installed_ids), set(installing_ids)
        for position, project in enumerate(self._projects):
            if project.project_id in changed:
                model_index = self.index(position, 0)
                self.dataChanged.emit(model_index, model_index)
