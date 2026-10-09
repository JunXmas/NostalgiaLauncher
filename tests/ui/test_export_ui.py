"""Xuất qua dialog thật, đổi bản chơi, giữ form và chặn thao tác khi game bận."""

from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFileDialog
from test_bridges import wait_until

from export_fixture import prepared_export
from nostalgia.api import Instance
from nostalgia.content import cfpack, mrpack
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control, press


@pytest.mark.usefixtures("qt_app")
@pytest.mark.parametrize(
    "archive_format,include_worlds,scale",
    [
        ("mrpack", False, 100),
        ("mrpack", True, 150),
        ("zip", False, 150),
        ("zip", True, 100),
    ],
)
def test_dialog_exports_selected_instance_and_worlds_without_small_window_overflow(
    tmp_path: Path,
    archive_format: str,
    include_worlds: bool,
    scale: int,
) -> None:
    launcher = prepared_export(tmp_path)
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            ui_sound=False,
            notification_sound=False,
            ui_scale=scale,
        )
    )
    launcher.save_instance(Instance("second", "1.20.1", "Another pack"))
    warnings: list[str] = []
    previous = qInstallMessageHandler(lambda _mode, _context, message: warnings.append(message))
    view, bridge = open_preview(launcher)
    try:
        view.resize(1024, 600)
        view.show()
        root_item = view.rootObject()
        root_item.setProperty("sessionSkipped", True)
        root_item.setProperty("currentIndex", 1)
        QTest.qWait(100)
        press(view, find_control(root_item, "openBackupDialog"))
        dialog = find_control(root_item, "modernBackupDialog")
        wait_until(lambda: bool(dialog.property("opened")))
        picker = find_control(dialog, "exportInstancePicker")
        for instance_id in ("second", "custom"):
            selected_index = next(
                position
                for position, instance in enumerate(cast(Any, bridge).instances)
                if instance["instanceId"] == instance_id
            )
            picker.choose(selected_index, False)
            assert dialog.property("instanceId") == instance_id
        if archive_format == "zip":
            press(view, find_control(dialog, "exportFormat-1"))
        if include_worlds:
            press(view, find_control(dialog, "exportIncludeWorlds"), Qt.Key.Key_Space)
        assert dialog.property("archiveFormat") == archive_format
        export_button = find_control(dialog, "exportSaveButton")
        assert export_button.property("clickable")
        origin = export_button.mapToScene(QPointF())
        assert origin.y() >= 0 and origin.y() + export_button.height() <= view.height()
        assert origin.x() >= 0 and origin.x() + export_button.width() <= view.width()
        destination = tmp_path / ("chosen." + archive_format)
        if archive_format == "mrpack" and scale == 100:
            file_picker = find_control(dialog, "exportSavePicker")
            file_picker.setProperty("options", QFileDialog.Option.DontUseNativeDialog.value)
            press(view, export_button)
            wait_until(lambda: bool(file_picker.property("visible")))
            file_picker.setProperty("currentFolder", QUrl.fromLocalFile(str(tmp_path)))
            QTest.qWait(300)
            filename_field = find_control(view, "fileNameTextField")
            filename_field.forceActiveFocus()
            QTest.keyClick(
                filename_field.window(), Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier
            )
            QGuiApplication.sendEvent(
                filename_field.window(),
                QKeyEvent(
                    QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, destination.name
                ),
            )
            QTest.keyClick(filename_field.window(), Qt.Key.Key_Tab)
            save_button = next(
                control
                for control in view.findChildren(QQuickItem)
                if control.inherits("QQuickAbstractButton") and control.property("text") == "Save"
            )
            center = save_button.mapToScene(
                QPointF(save_button.width() / 2, save_button.height() / 2)
            )
            QTest.mouseClick(save_button.window(), Qt.MouseButton.LeftButton, pos=center.toPoint())
        else:
            dialog.saveTo(destination.as_uri())
        storage = view.rootContext().contextProperty("storageBridge")
        wait_until(lambda: not storage.busy and bool(dialog.property("exportedPath")))
        assert destination.is_file() and not dialog.property("failed")
        assert len(launcher.list_instances()) == 2
        restored = tmp_path / "restored"
        if archive_format == "mrpack":
            assert mrpack.read_index(destination).name == "Gói của tôi"
            mrpack.apply_overrides(destination, restored)
        else:
            manifest = cfpack.read_manifest(destination)
            assert manifest.name == "Gói của tôi"
            cfpack.apply_overrides(destination, restored, manifest.overrides_prefix)
        assert (restored / "saves/My world/level.dat").exists() == include_worlds
        assert (restored / "mods/optional.jar.disabled").read_bytes() == b"disabled mod"
        assert dialog.property("opened")
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(previous)
    assert not [
        message
        for message in warnings
        if any(
            marker in message
            for marker in ("ReferenceError", "TypeError", "Binding loop", "Unable", "Cannot")
        )
    ]


@pytest.mark.usefixtures("qt_app")
def test_export_and_delete_refuse_to_run_while_main_worker_is_busy(tmp_path: Path) -> None:
    launcher = prepared_export(tmp_path)
    view, bridge = open_preview(launcher)
    storage = view.rootContext().contextProperty("storageBridge")
    errors: list[str] = []
    storage.failed.connect(errors.append)
    destination = tmp_path / "blocked.zip"
    try:
        bridge._set_busy(True)
        storage.exportModpack("custom", destination.as_uri(), "zip", False)
        wait_until(lambda: not storage.busy)
        storage.deletePermanently("custom")
        wait_until(lambda: not storage.busy)
        assert len(errors) == 2
        assert not destination.exists() and launcher.paths.instance_dir("custom").exists()
    finally:
        bridge._set_busy(False)
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
