"""Popup input must stop at the active modal, including its frame padding."""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from qt_controls import find_control, wheel

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize(
    "dialog_name",
    [
        "guideDialog",
        "supportDialog",
        "projectCreateInstance",
        "addAccountDialog",
        "modernQuickModpack",
        "confirmationModal",
        "accountMenu",
    ],
)
@pytest.mark.parametrize(
    "mouse_button",
    [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton],
)
def test_modal_consumes_frame_and_background_input(
    preview: Preview, dialog_name: str, mouse_button: Qt.MouseButton
) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 3 if dialog_name == "addAccountDialog" else 2)
    QTest.qWait(300)
    qml_factory = QQmlComponent(view.engine())
    qml_factory.setData(
        b"import QtQuick; MouseArea { z: 80; anchors.fill: parent; "
        b"acceptedButtons: Qt.AllButtons; property int presses: 0; "
        b"property int wheels: 0; property int taps: 0; "
        b"TapHandler { onTapped: parent.taps++; } onPressed: presses++; "
        b"onWheel: function(event) { wheels++; event.accepted = true; } }",
        QUrl(),
    )
    probe: Any = qml_factory.create(view.rootContext())
    assert probe is not None, [e.toString() for e in qml_factory.errors()]
    probe.setParent(view.contentItem())
    probe.setParentItem(view.contentItem())
    QTest.mouseClick(view, mouse_button, pos=QPointF(10, 10).toPoint())
    assert probe.property("presses") == 1
    dialog = find_control(root_item, dialog_name)
    if dialog_name == "confirmationModal":
        find_control(root_item, "confirmDialog").ask("Test", "Message", None)
    elif dialog_name in ("addAccountDialog", "modernQuickModpack"):
        dialog.setProperty("visible", True)
    else:
        dialog.open()
    QTest.qWait(350)
    surface = (
        find_control(
            root_item,
            "AddAccountDialogSurface"
            if dialog_name == "addAccountDialog"
            else "ModpackDialogSurface",
        )
        if dialog_name in ("addAccountDialog", "modernQuickModpack")
        else dialog.property("background")
    )
    for offset in (QPointF(8, 8), QPointF(surface.width() - 8, surface.height() - 8)):
        point = surface.mapToScene(offset).toPoint()
        QTest.mouseClick(view, mouse_button, pos=point)
        assert dialog.property("visible"), "Clicking the modal frame must not dismiss it"
        assert probe.property("taps") == (1 if mouse_button == Qt.MouseButton.LeftButton else 0), (
            "Modal frame leaked a tap to the page"
        )
        assert probe.property("presses") == 1, "Modal frame leaked a click to the page"
    wheel(view, surface)
    assert probe.property("wheels") == 0, "Modal leaked wheel input to the page"
    QTest.mouseClick(view, mouse_button, pos=QPointF(10, 10).toPoint())
    assert probe.property("presses") == 1, "Modal backdrop leaked a click to the page"
    if dialog_name == "confirmationModal":
        find_control(root_item, "confirmDialog").dismiss()
    elif dialog_name in ("addAccountDialog", "modernQuickModpack"):
        dialog.setProperty("visible", False)
    else:
        dialog.close()
    QTest.qWait(300)
    QTest.mouseClick(view, mouse_button, pos=QPointF(10, 10).toPoint())
    assert probe.property("presses") == 2, "Closing the modal must release the page"
    probe.setParentItem(None)
    probe.deleteLater()


@pytest.mark.parametrize(
    "dialog_name, action_name",
    [
        ("accountMenu", "openCosmeticLibrary"),
        ("supportDialog", "paymentClose"),
        ("confirmationModal", "confirmCancel"),
    ],
)
def test_popup_action_cannot_click_the_page(
    preview: Preview, dialog_name: str, action_name: str
) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    QTest.qWait(300)
    qml_factory = QQmlComponent(view.engine())
    qml_factory.setData(
        b"import QtQuick; MouseArea { z: 80; anchors.fill: parent; "
        b"property int presses: 0; property int taps: 0; "
        b"TapHandler { onTapped: parent.taps++; } onPressed: presses++; }",
        QUrl(),
    )
    probe: Any = qml_factory.create(view.rootContext())
    probe.setParent(view.contentItem())
    probe.setParentItem(view.contentItem())
    menu = find_control(root_item, dialog_name)
    if dialog_name == "confirmationModal":
        find_control(root_item, "confirmDialog").ask("Test", "Message", None)
    else:
        menu.open()
    QTest.qWait(350)
    button = find_control(root_item, action_name)
    point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=point.toPoint())
    QTest.qWait(300)
    assert root_item.property("currentIndex") == (7 if dialog_name == "accountMenu" else 0)
    assert not menu.property("visible")
    assert probe.property("presses") == 0, "Menu action also pressed the page below"
    assert probe.property("taps") == 0, "Menu action also tapped the page below"
    probe.setParentItem(None)
    probe.deleteLater()
