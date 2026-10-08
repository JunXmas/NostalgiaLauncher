"""Bấm hộp chọn mod trong QML thật, kiểm tra danh sách ảo hóa và mica ở cửa sổ nhỏ."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_host_popup import host_popup as host_popup
from test_minimal_preview import find_control, press


@pytest.mark.usefixtures("qt_app")
def test_paid_host_selects_mods_in_bounded_glass_popup(
    host_popup: tuple[Any, ...],
    tmp_path: Path,
) -> None:
    launcher, view, _bridge, root_item, host, warnings = host_popup
    game_dir = launcher.paths.instance_dir("a")
    (game_dir / "mods").mkdir()
    for file_name in ["sodium.jar", "private-custom.jar", "client-map.jar"]:
        (game_dir / "mods" / file_name).write_bytes(b"fixture")
    social = view.rootContext().contextProperty("socialBridge")
    social._snapshot = replace(
        social._snapshot, account=replace(social._snapshot.account, plus_lifetime=True)
    )
    social._plus_enabled = True
    social.changed.emit()
    sync_bridge = view.rootContext().contextProperty("roomSyncBridge")
    sync_bridge.set_gateway(object())
    host._plus_enabled = True
    host.changed.emit()
    view.rootContext().setContextProperty("plusFeaturesEnabled", True)
    host.openSetup()
    popup = find_control(root_item, "hostDialog")
    wait_until(lambda: popup.property("opened") and host._mod_selection.ready)
    QTest.qWait(100)
    assert host.syncAvailable and popup.property("sharePack")
    assert len(host._mod_selection.mods) == 3
    mod_list = find_control(root_item, "hostSharedModList")
    assert mod_list.property("count") == 3 and mod_list.property("height") > 0

    def visible_control(parent: Any, name: str) -> Any:
        if parent.objectName() == name:
            return parent
        for child in parent.childItems():
            found = visible_control(child, name)
            if found is not None:
                return found
        return None

    checkbox = visible_control(mod_list, "shareMod_private-custom.jar")
    assert checkbox is not None
    assert checkbox.property("checked")
    screen = QGuiApplication.primaryScreen()
    assert screen is not None
    press(view, checkbox)
    wait_until(
        lambda: not visible_control(mod_list, "shareMod_private-custom.jar").property("checked")
    )
    assert host._mod_selection.excluded_for("a") == frozenset({"mods/private-custom.jar"})
    assert (game_dir / "mods/private-custom.jar").read_bytes() == b"fixture"
    assert not (game_dir / "mods/private-custom.jar.disabled").exists()
    assert mod_list.property("height") <= 240
    screen = QGuiApplication.primaryScreen()
    assert screen is not None
    assert view.grabWindow().save(str(tmp_path / "host-mod-selection.png"))
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        150, False, False, True, "vi"
    )
    QTest.qWait(100)
    assert popup.property("height") <= 552
    assert mod_list.property("height") <= 360
    launch = find_control(root_item, "hostLaunchButton")
    position = launch.mapToScene(QPointF())
    assert 0 <= position.y() <= view.height() - launch.height()
    assert 0 <= position.x() <= view.width() - launch.width()
    scroll = find_control(root_item, "hostSetupScroll")
    scroll.setProperty("contentY", scroll.property("maxY"))
    QTest.qWait(60)
    assert view.grabWindow().save(str(tmp_path / "host-mod-selection-small.png"))
    assert not warnings
