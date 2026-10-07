"""Native delete confirmation must be above the instance manager's Overlay popup."""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview
from test_modern_workspace import prepare_instance

from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_delete_cancel_and_escape_keep_manager_then_accept_trashes_once(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    prepare_instance(preview)
    press(view, find_item(root_item, "manageInstance-survival"))
    manager = find_control(root_item, "modernInstanceManager")
    wait_until(lambda: bool(manager.property("opened")))
    press(view, find_item(manager.property("contentItem"), "instanceSection-3"))
    confirmation = find_control(root_item, "confirmDialog")
    accepted: list[bool] = []
    confirmation.accepted.connect(lambda: accepted.append(True))
    for cancel_key in (None, Qt.Key.Key_Escape):
        press(view, find_control(root_item, "instanceTrash"))
        modal = find_control(root_item, "confirmationModal")
        wait_until(lambda modal=modal: bool(modal.property("opened")))
        assert modal.property("z") > manager.property("z")
        assert manager.property("opened")
        assert len(launcher.list_instances()) == 1
        if cancel_key is None:
            press(view, find_control(root_item, "confirmCancel"))
        else:
            QTest.keyClick(view, cancel_key)
        wait_until(lambda: not confirmation.property("visible"))
        assert manager.property("opened") and accepted == []
    press(view, find_control(root_item, "instanceTrash"))
    wait_until(lambda: bool(find_control(root_item, "confirmationModal").property("opened")))
    press(view, find_control(root_item, "confirmAccept"))
    wait_until(lambda: not launcher.list_instances())
    wait_until(lambda: not manager.property("visible"))
    assert accepted == [True]
    confirmation.accept()
    assert accepted == [True]
