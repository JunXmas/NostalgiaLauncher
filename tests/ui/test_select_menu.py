"""Long version menus fit the window and keep source indices after search."""

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QMetaObject, QObject, QPointF, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest
from test_bridges import wait_until

from nostalgia.ui.app import QML_DIR

pytestmark = pytest.mark.usefixtures("qt_app")


def find_item(root_item: Any, name: str) -> Any:
    if root_item.objectName() == name:
        return root_item
    for child in root_item.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None


@pytest.mark.parametrize("scale", [100, 150])
def test_long_menu_is_bounded_searchable_and_selects_original_index(
    tmp_path: Path, scale: int
) -> None:
    path = tmp_path / "Menu.qml"
    path.write_text(
        'import QtQuick\nimport "' + (QML_DIR / "preview").as_uri() + '" as Preview\n'
        "Item { width:1024; height:600; property int activatedIndex:-1; "
        "QtObject { id: preferences; property bool reducedMotion:true; property int uiScale:"
        + str(scale)
        + "; } "
        "Component.onCompleted: Preview.GlassTheme.preferences=preferences; "
        "Item { id: backdrop; anchors.fill:parent; } "
        'Preview.Select { objectName:"versions"; x:380; y:350; width:240; '
        "menuBackdrop:backdrop; "
        'model: Array.from({length:60},function(_,i){return "1."+i+".1";}); '
        "onActivated:function(index){parent.activatedIndex=index;} } }"
    )
    warnings: list[str] = []
    qInstallMessageHandler(lambda _level, _ctx, message: warnings.append(message))
    view = QQuickView()
    try:
        view.setSource(QUrl.fromLocalFile(str(path)))
        assert not view.errors()
        view.show()
        view.requestActivate()
        root_item = view.rootObject()
        assert root_item is not None
        select = root_item.findChild(QObject, "versions")
        assert isinstance(select, QQuickItem)
        menu = root_item.findChild(QObject, "versionsMenu")
        assert menu is not None
        center = select.mapToScene(QPointF(40, 20)).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)
        wait_until(lambda: bool(menu.property("opened")))
        assert menu.property("height") <= view.height() * 0.48 + 1
        content_item = menu.property("contentItem")
        scene = content_item.mapToScene(QPointF())
        assert scene.y() >= 0 and scene.y() + content_item.height() <= view.height()
        mica = root_item.findChild(QObject, "versionsMenuMica")
        assert isinstance(mica, QQuickItem)
        mica_origin = mica.mapToScene(QPointF())
        assert mica.property("backdropRect").x() == pytest.approx(mica_origin.x())
        assert mica.property("backdropRect").y() == pytest.approx(mica_origin.y())
        assert mica.property("clip")
        search = find_item(content_item, "versionsSearch")
        search.setProperty("text", "1.57.")
        choices = find_item(content_item, "versionsChoices")
        wait_until(lambda: choices.property("count") == 1)
        QTest.keyClick(view, Qt.Key.Key_Return)
        wait_until(lambda: root_item.property("activatedIndex") == 57)
        assert select.property("currentIndex") == 57
        assert not menu.property("opened")
        select.setProperty("model", ["Alpha", "Beta"])
        QMetaObject.invokeMethod(menu, "open")
        wait_until(lambda: bool(menu.property("opened")))
        assert choices.property("count") == 2
        assert not search.isVisible()
        assert not warnings
    finally:
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(None)
