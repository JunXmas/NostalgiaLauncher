"""Luồng preview dùng bàn phím, tùy chọn được lưu, sao lưu/khôi phục qua UI thật."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from modern_window import go, open_modern
from PySide6.QtCore import QObject, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until

from nostalgia.api import Launcher
from nostalgia.errors import InstanceError
from nostalgia.instance.model import Instance
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


def make_preview(tmp_path: Path) -> Launcher:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    return launcher


def test_saved_display_preferences_and_every_page_loads_quietly(tmp_path: Path) -> None:
    launcher = make_preview(tmp_path)
    view, _bridge, root_item = open_modern(launcher)
    compact = go(root_item, 6, "compactUiToggle")
    view.requestActivate()
    compact.forceActiveFocus()
    wait_until(lambda: bool(compact.property("activeFocus")))
    QTest.keyClick(view, Qt.Key.Key_Space)
    assert launcher.load_settings().compact_ui
    settings_bridge = view.rootContext().contextProperty("settingsBridge")
    settings_bridge.setAppearance(150, True, True, False, "en")
    QTest.qWait(100)
    assert launcher.load_settings().ui_scale == 150
    assert launcher.load_settings().language == "en"
    heading = find_item(root_item, "appearanceHeading")
    assert heading is not None and heading.property("caption") == "Appearance & language"
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        view.resize(1024, 600)
        for page_index in range(8):
            go(root_item, page_index)
            QTest.qWait(100)
        assert warnings == []
    finally:
        qInstallMessageHandler(None)
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()


def test_ui_backup_restore_and_trash_preserve_world(tmp_path: Path) -> None:
    launcher = make_preview(tmp_path)
    launcher.save_instance(Instance("survival", "1.20.1", display_name="Sinh tồn"))
    source = launcher.paths.instance_dir("survival") / "saves" / "level.dat"
    source.parent.mkdir()
    source.write_bytes(b"world")
    view, bridge, root_item = open_modern(launcher)
    view.requestActivate()
    go(root_item, 1, "minimalInstances")
    storage = view.rootContext().contextProperty("storageBridge")
    editor = root_item.findChild(QObject, "modernInstanceManager")
    assert editor is not None
    editor.openFor(bridge.instances[0])
    editor.setProperty("section", 3)
    backup = find_item(editor.property("contentItem"), "instanceBackup")
    assert backup is not None and backup.property("clickable")
    backup.metaObject().invokeMethod(backup, "clicked")
    wait_until(lambda: not storage.busy and bool(launcher.list_instance_backups()))
    wait_until(lambda: bool(editor.property("storageNote")))
    editor.setProperty("visible", False)
    manager = root_item.findChild(QObject, "legacyBackupDialog")
    assert manager is not None
    manager.openDialog()
    manager.setProperty("selectedBackup", str(launcher.list_instance_backups()[0].path))
    restore_name = manager.findChild(QObject, "restoreName")
    assert restore_name is not None
    restore_name.setProperty("text", "restored")
    button = manager.findChild(QObject, "restoreBackupButton")
    assert button is not None
    wait_until(lambda: bool(button.property("clickable")))
    button.metaObject().invokeMethod(button, "clicked")
    wait_until(lambda: not storage.busy and len(launcher.list_instances()) == 2)
    assert (
        launcher.paths.instance_dir("restored") / "saves" / "level.dat"
    ).read_bytes() == b"world"
    storage.moveToTrash("survival")
    wait_until(lambda: not storage.busy)
    assert [i.instance_id for i in launcher.list_instances()] == ["restored"]
    storage.restoreTrash(storage.trash[0]["trashId"])
    wait_until(lambda: not storage.busy)
    assert source.read_bytes() == b"world"
    assert {i["instanceId"] for i in bridge.instances} == {"survival", "restored"}
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def test_persistent_failure_retries_once_after_network_recovers(tmp_path: Path) -> None:
    view, _bridge, _root_item = open_modern(make_preview(tmp_path))
    worker = view.rootContext().contextProperty("storageBridge")
    attempts: list[int] = []

    def temporarily_unavailable() -> None:
        attempts.append(1)
        if len(attempts) == 1:
            raise InstanceError("offline — thử lại khi có mạng")

    worker.run_in_background(temporarily_unavailable)
    wait_until(lambda: worker.canRetry)
    banner = view.rootObject().findChild(QObject, "errorBanner")
    QTest.qWait(6200)
    assert banner is not None and banner.property("visible"), (
        "lỗi phải còn cho đến khi người dùng đóng hoặc thử lại"
    )
    retry = banner.findChild(QObject, "retryButton")
    assert retry is not None
    retry.forceActiveFocus()
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_until(lambda: not worker.busy)
    assert len(attempts) == 2 and not worker.canRetry
    worker.retry()
    assert len(attempts) == 2
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()
