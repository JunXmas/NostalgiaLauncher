"""Dựng cửa sổ thật (giao diện duy nhất) cho test, bỏ qua màn đăng nhập, và chuyển trang."""

from __future__ import annotations

from typing import Any

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem, QQuickView
from qml_tree import find_item
from test_bridges import wait_until

from nostalgia.api import Launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.window import open_window


def open_modern(launcher: Launcher) -> tuple[QQuickView, LauncherBridge, QQuickItem]:
    view, bridge = open_window(launcher)
    root_item = view.rootObject()
    assert root_item is not None, [error.toString() for error in view.errors()]
    root_item.setProperty("sessionSkipped", True)
    view.show()
    QGuiApplication.processEvents()
    return view, bridge, root_item


def go(root_item: QQuickItem, page_index: int, ready: str = "") -> Any:
    """Chuyển trang; có `ready` thì đợi item mang tên đó xuất hiện rồi trả về nó."""
    root_item.setProperty("currentIndex", page_index)
    QGuiApplication.processEvents()
    if not ready:
        return None
    wait_until(lambda: find_item(root_item, ready) is not None)
    return find_item(root_item, ready)
