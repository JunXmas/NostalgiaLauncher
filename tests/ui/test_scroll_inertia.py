"""Actual pointer/wheel input: drift after release, nested virtual lists and focus theme."""

from __future__ import annotations

from typing import Any, cast

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlProperty
from PySide6.QtTest import QTest
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
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        100, False, False, True, "vi"
    )
    scroll.scrollBy(70, False)
    assert scroll.property("settling")
    view.hide()
    QGuiApplication.processEvents()
    assert not scroll.property("settling")


def test_version_menu_reverses_from_visible_position_and_reaches_latest(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    catalog_bridge: Any = view.rootContext().contextProperty("catalogBridge")
    catalog_bridge._released = [
        {"versionId": f"1.{n}.1", "major": f"1.{n}"} for n in range(40, 0, -1)
    ]
    catalog_bridge._preset_versions = ["1.40.1"]
    catalog_bridge.releasedVersionsChanged.emit()
    catalog_bridge.presetVersionsChanged.emit()
    press(view, find_control(root_item, "createModernInstance"))
    dialog = find_control(root_item, "modernCreateDialog")
    dialog.setProperty("loaderKind", "vanilla")
    select = find_control(root_item, "createGameVersion")
    press(view, select, Qt.Key.Key_Space)
    scroll = find_control(root_item, "createGameVersionChoices")
    controller = find_control(root_item, "createGameVersionMotion")
    wait_until(lambda: scroll.isVisible() and scroll.property("contentHeight") > 1000)
    QTest.qWait(250)
    wheel(view, scroll, angle=0, pixels=-400)
    QTest.qWait(70)
    visible_position = float(scroll.property("contentY"))
    assert 0 < visible_position < 400
    assert controller.property("settling")
    wheel(view, scroll, angle=0, pixels=70)
    reversal_position = float(scroll.property("contentY"))
    assert float(controller.property("destination")) == pytest.approx(
        max(0, reversal_position - 70)
    )
    QTest.qWait(80)
    assert float(scroll.property("contentY")) < reversal_position
    # Reverse before reaching the queued lower edge; it must never drag us down.
    wheel(view, scroll, angle=0, pixels=-3000)
    QTest.qWait(60)
    wheel(view, scroll, angle=0, pixels=3000)
    at_edge = float(scroll.property("contentY"))
    assert float(controller.property("destination")) == 0
    QTest.qWait(90)
    assert float(scroll.property("contentY")) < at_edge
    wait_until(lambda: not controller.property("settling"))
    assert float(scroll.property("contentY")) == pytest.approx(0)
    search = find_control(root_item, "createGameVersionSearch")
    search.setProperty("text", "1.40.1")
    QTest.keyClick(view, Qt.Key.Key_Return)
    assert dialog.property("gameVersion") == "1.40.1"
    catalog_bridge.releasedVersionsChanged.emit()
    assert dialog.property("gameVersion") == "1.40.1"
    assert dialog.property("canCreate")


def test_log_bounds_do_not_bounce_or_pull_reader_back_to_tail(preview: Preview) -> None:
    _launcher, view, bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 5)
    page = find_control(root_item, "logPage")
    scroll = find_control(root_item, "logList")
    controller = find_control(root_item, "logMotion")
    feed = cast(Any, bridge.property("gameLog"))
    feed.begin_session()
    for number in range(5200):
        feed.receive(f"[main/INFO]: {number} " + "Long wrapped line " * (number % 4 + 1))
    feed.drain()
    wait_until(lambda: scroll.property("count") == 5000)
    QTest.qWait(120)
    wheel(view, scroll, angle=0, pixels=-3000)
    QTest.qWait(150)
    assert float(scroll.property("contentY")) <= float(controller.property("maxY")) + 1
    start = scroll.mapToScene(QPointF(scroll.width() - 25, scroll.height() * 0.8)).toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    for offset in range(20, 121, 20):
        QTest.mouseMove(view, start - QPoint(0, offset))
        QTest.qWait(20)
        assert float(scroll.property("contentY")) <= float(controller.property("maxY")) + 1
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=start - QPoint(0, 120))
    QTest.qWait(120)
    wheel(view, scroll, angle=0, pixels=500)
    QTest.qWait(100)
    assert not page.property("followTail")
    position = float(scroll.property("contentY")) - float(controller.property("minY"))
    for number in range(20):
        feed.receive(f"[main/INFO]: added {number}")
    feed.drain()
    QTest.qWait(120)
    assert not page.property("followTail")
    assert float(scroll.property("contentY")) - float(controller.property("minY")) < position + 10
    # The virtualized origin may move after old rows are removed; it is not zero.
    wheel(view, scroll, angle=0, pixels=1_000_000)
    wait_until(lambda: not controller.property("settling"))
    assert float(scroll.property("contentY")) == pytest.approx(
        float(controller.property("minY")), abs=1
    )
    for _ in range(5):
        wheel(view, scroll, angle=0, pixels=1000)
        QTest.qWait(20)
    assert not controller.property("settling")
    assert float(scroll.property("contentY")) == pytest.approx(
        float(controller.property("minY")), abs=1
    )
    feed.end_session()
