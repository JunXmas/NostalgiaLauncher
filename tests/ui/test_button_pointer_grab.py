"""Buttons consume one tap while still allowing their scroll view to drag."""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.ui.app import QML_DIR

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("button_type", ["Preview.Button", "Legacy.ActionButton"])
def test_button_claims_click_and_allows_flickable_drag(
    tmp_path: Path, button_type: str, preview: Preview
) -> None:
    path = tmp_path / "Pointer.qml"
    path.write_text(
        'import QtQuick\nimport "' + QML_DIR.as_uri() + '" as Legacy\n'
        'import "' + (QML_DIR / "preview").as_uri() + '" as Preview\n'
        "Item { id:root; width:400; height:240; property int clicks:0; property int leaks:0; "
        "Item { anchors.fill:parent; TapHandler { onTapped:root.leaks++; } } "
        + button_type
        + ' { objectName:"topButton"; x:30; y:30; width:200; height:50; label:"Top"; '
        "onClicked: root.clicks++; } "
        'Preview.InertialScroll { objectName:"scroll"; y:120; width:parent.width; height:120; '
        "contentHeight:1000; "
        + button_type
        + ' { objectName:"button"; x:30; y:80; width:200; height:50; label:"Test"; '
        "onClicked: root.clicks++; } } }"
    )
    view = QQuickView()
    view.rootContext().setContextProperty(
        "notifier", preview[1].rootContext().contextProperty("notifier")
    )
    try:
        view.setSource(QUrl.fromLocalFile(str(path)))
        assert not view.errors()
        view.show()
        view.requestActivate()
        QTest.qWait(100)
        root_item = view.rootObject()
        assert root_item is not None
        button = root_item.findChild(QObject, "button")
        scroll = root_item.findChild(QObject, "scroll")
        assert isinstance(button, QQuickItem) and scroll is not None
        top_button = root_item.findChild(QObject, "topButton")
        assert isinstance(top_button, QQuickItem)
        top_center = top_button.mapToScene(QPointF(80, 25)).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=top_center)
        assert root_item.property("clicks") == 1
        assert root_item.property("leaks") == 0, (
            "A button must consume the tap above another control"
        )
        center = button.mapToScene(QPointF(80, 25)).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)
        assert root_item.property("clicks") == 2
        assert root_item.property("leaks") == 0
        QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=center)
        for distance in (12, 30, 55, 80):
            QTest.mouseMove(view, center - QPoint(0, distance), 20)
        QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=center - QPoint(0, 80))
        QTest.qWait(100)
        assert scroll.property("contentY") > 0, "Button must allow the parent to take a drag"
        assert root_item.property("clicks") == 2, "A drag must not trigger the button"
        assert root_item.property("leaks") == 0
    finally:
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
