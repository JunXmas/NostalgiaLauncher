"""Thao tác bàn phím và cuộn Qt, xử lý kích hoạt cửa sổ trước khi gửi phím."""

from typing import Any

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication, QWheelEvent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest


def find_control(root_item: Any, name: str) -> Any:
    result = root_item.findChild(QObject, name)
    assert result is not None, name
    return result


def press(view: QQuickView, control: Any, key: Qt.Key = Qt.Key.Key_Return) -> None:
    view.requestActivate()
    QGuiApplication.processEvents()
    control.forceActiveFocus()
    QTest.keyClick(view, key)
    QGuiApplication.processEvents()


def wheel(view: QQuickView, scroll: Any, angle: int = -120, pixels: int = 0) -> None:
    position = scroll.mapToScene(QPointF(scroll.width() / 2, scroll.height() / 2))
    event = QWheelEvent(
        position,
        position,
        QPoint(0, pixels),
        QPoint(0, angle),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QGuiApplication.sendEvent(view, event)
