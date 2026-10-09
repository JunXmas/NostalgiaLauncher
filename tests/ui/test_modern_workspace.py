"""Quản lý bản chơi, nội dung đã cài và chuyển động qua tương tác Qt thật."""

from __future__ import annotations

import json
from typing import Any, cast

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.instance.model import Instance
from qt_controls import find_control, press, wheel

pytestmark = pytest.mark.usefixtures("qt_app")


def prepare_instance(context: Preview) -> None:
    launcher, _view, bridge, root_item = context
    version_id = "fabric-loader-0.16.0-1.20.1"
    version_path = launcher.paths.version_json(version_id)
    version_path.parent.mkdir(parents=True)
    version_path.write_text(
        json.dumps(
            {
                "id": version_id,
                "jar": "1.20.1",
                "mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient",
                "libraries": [{"name": "net.fabricmc:fabric-loader:0.16.0"}],
            }
        )
    )
    launcher.save_instance(Instance("survival", version_id, display_name="Sinh tồn"))
    bridge.instancesChanged.emit()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    QTest.qWait(300)


@pytest.mark.parametrize("scale", [100, 150])
def test_small_instance_action_keeps_its_complete_label(preview: Preview, scale: int) -> None:
    _launcher, view, _bridge, root_item = preview
    prepare_instance(preview)
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, False, True, "vi"
    )
    QTest.qWait(100)
    action = find_control(root_item, "instanceAction-survival")
    caption = find_control(action, "buttonCaption")
    assert caption.width() >= caption.implicitWidth() > 0
    origin = caption.mapToItem(action, QPointF())
    assert origin.x() >= 4
    assert origin.x() + caption.width() <= action.width() - 4
    assert origin.y() >= 0
    assert origin.y() + caption.height() <= action.height()


def test_manager_saves_real_settings_and_keeps_sections_scrollable(preview: Preview) -> None:
    launcher, view, bridge, root_item = preview
    prepare_instance(preview)
    action = find_item(root_item, "manageInstance-survival")
    assert action is not None
    press(view, action)
    dialog = find_control(root_item, "modernInstanceManager")
    wait_until(lambda: bool(dialog.property("opened")))
    find_control(root_item, "instanceName").setProperty("text", "Sinh tồn cùng bạn")
    press(view, find_item(dialog.property("contentItem"), "instanceSection-2"))
    find_control(root_item, "instanceHeap").setProperty("text", "4096")
    press(view, find_control(root_item, "instanceSave"))
    wait_until(lambda: not dialog.property("visible"))
    saved = launcher.list_instances()[0]
    assert saved.display_name == "Sinh tồn cùng bạn"
    assert saved.max_heap_megabytes == 4096
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        150, False, False, True, "vi"
    )
    dialog.openFor(cast(Any, bridge).instances[0])
    wait_until(lambda: bool(dialog.property("opened")))
    QTest.qWait(300)
    form = find_control(root_item, "instanceManagerScroll")
    assert form.property("height") > 80
    assert form.property("maxY") > 0
    wheel(view, form)
    QTest.qWait(100)
    assert form.property("contentY") > 0
    press(view, find_control(root_item, "instanceSave"))
    wait_until(lambda: not dialog.property("visible"))


def test_installed_opens_modern_view_and_toggle_changes_real_file(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    prepare_instance(preview)
    mods = launcher.paths.instance_dir("survival") / "mods"
    mods.mkdir()
    (mods / "sample.jar").write_bytes(b"manual mod fixture")
    root_item.setProperty("currentIndex", 2)
    QTest.qWait(300)
    press(view, find_control(root_item, "openModernInstalled"))
    panel = find_control(root_item, "modernInstalledContent")
    assert panel.property("visible")
    assert root_item.findChild(type(panel), "contentPage") is None
    toggle = find_item(root_item, "installedToggle-sample.jar")
    assert toggle is not None
    press(view, toggle, Qt.Key.Key_Space)
    assert not (mods / "sample.jar").exists()
    assert (mods / "sample.jar.disabled").is_file()
    refreshed = find_item(root_item, "installedToggle-sample.jar")
    assert refreshed is not None
    press(view, refreshed, Qt.Key.Key_Space)
    assert (mods / "sample.jar").is_file()


def test_navigation_blocks_spin_then_settle_and_reduce_motion_stops_them(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    block = find_item(root_item, "navigationBlock-2")
    navigation_action = find_item(root_item, "navigationEntry-2")
    assert block is not None and navigation_action is not None
    position = navigation_action.mapToScene(
        QPointF(navigation_action.width() / 2, navigation_action.height() / 2)
    )
    QTest.mouseMove(view, QPoint(round(position.x()), round(position.y())))
    wait_until(lambda: float(block.property("velocity")) > 0.05)
    assert block.property("spinning")
    QTest.mouseMove(view, QPoint(view.width() - 5, view.height() - 5))
    wait_until(lambda: not block.property("spinning"))
    wait_until(lambda: block.property("turn") == 0 and block.property("velocity") == 0)
    view.rootContext().contextProperty("settingsBridge").setAppearance(100, False, True, True, "vi")
    navigation_action.forceActiveFocus()
    turn = block.property("turn")
    QTest.qWait(150)
    assert block.property("turn") == turn
