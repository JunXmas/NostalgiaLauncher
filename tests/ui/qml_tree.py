"""Đi cây item của QtQuick để tìm theo `objectName`.

`findChild` của Qt đi theo cây QObject, mà delegate của `Repeater`/`ListView` không có cha
QObject (model giữ chúng) — nên mọi thứ dựng trong delegate đều vô hình với `findChild`.
Cây item thì vẫn đủ, nên đi bằng `childItems()`.
"""

from __future__ import annotations

from PySide6.QtQuick import QQuickItem


def find_item(node: QQuickItem, name: str) -> QQuickItem | None:
    if node.objectName() == name:
        return node
    for child in node.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None
