"""Actual pointer/wheel input: drift after release, nested virtual lists and focus theme."""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlProperty
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from qt_controls import find_control, press, wheel

pytestmark = pytest.mark.usefixtures("qt_app")


def test_drag_release_coasts_and_reduced_motion_stops_drift(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        100, False, False, True, "vi"
    )
    root_item.setProperty("sessionSkipped", True)
    scroll = find_control(root_item, "homeScroll")
    # QQmlProperty removes the layout binding; setProperty would allow a late
    # font/image layout to replace our tall fixture during the drag.
    assert QQmlProperty(scroll, "contentHeight").write(2400)
    # The controller must coast even when Qt does not issue a native flick.
    scroll.setProperty("maximumFlickVelocity", 0)
    start = scroll.mapToScene(QPointF(scroll.width() - 25, scroll.height() * 0.8)).toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    for offset in range(20, 221, 20):
        QTest.mouseMove(view, start - QPoint(0, offset))
        QTest.qWait(20)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=start - QPoint(0, 220))
    at_release = float(scroll.property("contentY"))
    assert at_release > 50
    assert scroll.property("settling"), {
        name: scroll.property(name)
        for name in (
            "contentY",
            "contentHeight",
            "maxY",
            "destination",
            "verticalVelocity",
            "flicking",
        )
    }
    QTest.qWait(120)
    assert float(scroll.property("contentY")) > at_release + 10
    wait_until(lambda: not scroll.property("settling"))
    assert float(scroll.property("contentY")) <= float(scroll.property("maxY"))
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    for offset in range(20, 121, 20):
        QTest.mouseMove(view, start - QPoint(0, offset))
        QTest.qWait(20)
    QTest.qWait(160)  # holding still before release must not create momentum
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=start - QPoint(0, 120))
    held_release = float(scroll.property("contentY"))
    QTest.qWait(120)
    assert not scroll.property("settling")
    assert float(scroll.property("contentY")) == pytest.approx(held_release)
    view.rootContext().contextProperty("settingsBridge").setAppearance(100, False, True, True, "vi")
    start = scroll.mapToScene(QPointF(scroll.width() - 25, scroll.height() * 0.8)).toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    for offset in range(20, 121, 20):
        QTest.mouseMove(view, start - QPoint(0, offset))
        QTest.qWait(20)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=start - QPoint(0, 120))
    at_release = float(scroll.property("contentY"))
    QTest.qWait(120)
    assert not scroll.property("settling")
    assert float(scroll.property("contentY")) == pytest.approx(at_release)


def test_version_list_has_pixel_inertia_and_selected_chip_has_no_square_focus(
    preview: Preview,
) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    catalog_bridge: Any = view.rootContext().contextProperty("catalogBridge")
    catalog_bridge._released = [{"versionId": f"1.{n}.1", "major": f"1.{n}"} for n in range(1, 30)]
    catalog_bridge.releasedVersionsChanged.emit()
    press(view, find_control(root_item, "createModernInstance"))
    dialog = find_control(root_item, "modernCreateDialog")
    dialog.setProperty("loaderKind", "vanilla")
    dialog.setProperty("expandedMajor", "1.1")
    QTest.qWait(300)
    scroll = find_control(root_item, "majorListScroll")
    wheel(view, scroll, angle=0, pixels=-70)
    before = float(scroll.property("contentY"))
    QTest.qWait(120)
    assert before < float(scroll.property("contentY")) < 70
    wait_until(lambda: abs(float(scroll.property("contentY")) - 70) < 0.5)
    find_control(root_item, "majorListMotion").stopMotion()
    scroll.setProperty("contentY", 0)
    dialog.setProperty("expandedMajor", "1.1")
    QTest.qWait(100)
    chip = find_item(dialog, "versionChip-1.1.1")
    assert chip is not None
    press(view, chip)
    assert dialog.property("gameVersion") == "1.1.1"
    legacy = find_control(chip, "legacyButtonFocus")
    assert not legacy.property("visible")
    modern = find_control(chip, "modernButtonFace")
    assert modern.property("visible") and modern.property("radius") > 0
    QGuiApplication.processEvents()
    # Repeated wheel input at a clamped destination must not fall through to
    # native Qt scrolling while the visible content is still approaching it.
    controller = find_control(root_item, "majorListMotion")
    controller.stopMotion()
    limit = float(controller.property("maxY"))
    scroll.setProperty("contentY", limit - 300)
    wheel(view, scroll, angle=0, pixels=-1000)
    before_edge = float(scroll.property("contentY"))
    wheel(view, scroll, angle=0, pixels=-1000)
    assert float(scroll.property("contentY")) == pytest.approx(before_edge)
    wait_until(lambda: not controller.property("settling"))
    assert float(scroll.property("contentY")) == pytest.approx(float(controller.property("maxY")))
