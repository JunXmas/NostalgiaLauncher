"""Mô hình danh sách theo khoá cho các hàng dạng dict (danh sách đã cài, tài khoản...).

`sync(rows)` nhận danh sách mới và chỉ phát những thay đổi tối thiểu: hàng mất -> gỡ, hàng
đổi -> dataChanged, hàng mới -> nối. Không bao giờ reset, nên ListView giữ vị trí cuộn khi
người dùng bật/tắt hay gỡ một mục ở giữa danh sách.
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

FIRST_ROLE = Qt.ItemDataRole.UserRole + 1


class KeyedRowModel(QAbstractListModel):
    def __init__(self, roles: tuple[str, ...], key: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._roles = roles
        self._key = key
        self._rows: list[dict[str, Any]] = []

    def rowCount(self, _parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._rows)

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            FIRST_ROLE + offset: QByteArray(name.encode())
            for offset, name in enumerate(self._roles)
        }

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = FIRST_ROLE) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        return self._rows[index.row()].get(self._roles[role - FIRST_ROLE])

    @property
    def rows(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._rows]

    def sync(self, rows: list[dict[str, Any]]) -> None:
        wanted = {row[self._key]: row for row in rows}
        # 1) gỡ hàng không còn, đi từ cuối để chỉ số không trượt
        for position in range(len(self._rows) - 1, -1, -1):
            if self._rows[position][self._key] not in wanted:
                self.beginRemoveRows(QModelIndex(), position, position)
                del self._rows[position]
                self.endRemoveRows()
        # 2) cập nhật hàng đổi
        for position, existing in enumerate(self._rows):
            fresh = wanted[existing[self._key]]
            if fresh != existing:
                self._rows[position] = dict(fresh)
                model_index = self.index(position, 0)
                self.dataChanged.emit(model_index, model_index)
        # 3) nối hàng mới theo thứ tự danh sách mới
        known = {row[self._key] for row in self._rows}
        fresh_rows = [row for row in rows if row[self._key] not in known]
        if fresh_rows:
            first = len(self._rows)
            self.beginInsertRows(QModelIndex(), first, first + len(fresh_rows) - 1)
            self._rows.extend(dict(row) for row in fresh_rows)
            self.endInsertRows()
