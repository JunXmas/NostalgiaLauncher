"""Kiểm tra modal mới bằng thao tác thật: dữ liệu khôi phục và vùng cuộn nhỏ."""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_select_menu import find_item

from nostalgia.api import Found, Launcher
from nostalgia.instance.model import Instance
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control, press, wheel

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("scale", [100, 150])
def test_backup_is_modal_and_restores_a_separate_world(tmp_path: Path, scale: int) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
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
    launcher.create_instance(Instance("survival", "1.20.1", "Sinh tồn"))
    source = launcher.paths.instance_dir("survival") / "saves" / "level.dat"
    source.parent.mkdir()
    source.write_bytes(b"world-before")
    launcher.backup_instance("survival")
    source.write_bytes(b"world-after")
    launcher.create_instance(Instance("creative", "1.20.1", "Sáng tạo"))
    launcher.trash_instance("creative")
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    view, _bridge = open_preview(launcher)
    try:
        view.resize(1024, 600)
        view.show()
        root_item = view.rootObject()
        root_item.setProperty("sessionSkipped", True)
        root_item.setProperty("currentIndex", 1)
        QTest.qWait(70)
        press(view, find_control(root_item, "openBackupDialog"))
        dialog = find_control(root_item, "modernBackupDialog")
        wait_until(lambda: bool(dialog.property("opened")))
        assert dialog.property("modal") and dialog.property("dim")
        assert dialog.property("y") >= 0
        assert dialog.property("height") <= view.height() - 40
        press(view, find_control(dialog, "openLegacyBackups"))
        dialog = find_control(root_item, "legacyBackupDialog")
        wait_until(lambda: bool(dialog.property("opened")))
        press(view, find_item(view.contentItem(), "backupRecord-0"))
        find_control(dialog, "restoreName").setProperty("text", "restored")
        restore_button = find_control(dialog, "restoreBackupButton")
        p = restore_button.mapToScene(QPointF())
        assert p.y() > 0 and p.y() + restore_button.height() <= view.height()
        press(view, restore_button)
        storage = view.rootContext().contextProperty("storageBridge")
        wait_until(lambda: not storage.busy and len(launcher.list_instances()) == 2)
        assert (
            launcher.paths.instance_dir("restored") / "saves" / "level.dat"
        ).read_bytes() == b"world-before"
        assert source.read_bytes() == b"world-after"
        trash_button = find_item(view.contentItem(), "restoreTrash-0")
        assert trash_button is not None
        trash_position = trash_button.mapToScene(QPointF())
        assert (
            dialog.property("x")
            <= trash_position.x()
            < dialog.property("x") + dialog.property("width")
        )
        press(view, trash_button)
        wait_until(lambda: not storage.busy and len(launcher.list_instances()) == 3)
        assert any(i.instance_id == "creative" for i in launcher.list_instances())
        QTest.keyClick(view, Qt.Key.Key_Escape)
        wait_until(lambda: not dialog.property("visible"))
        assert not warnings
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(None)


def test_import_error_stays_in_modal_and_scrolling_does_not_move_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            ui_sound=False,
            notification_sound=False,
            ui_scale=150,
        )
    )
    external = tmp_path / "prism" / ".minecraft"
    (external / "saves").mkdir(parents=True)
    (external / "saves" / "level.dat").write_bytes(b"import-world")
    found = Found("PrismLauncher", "Prism world", external, "1.20.1", "vanilla")
    monkeypatch.setattr(Launcher, "scan_external_launchers", lambda _self: (found,))
    view, _bridge = open_preview(launcher)
    try:
        view.resize(1024, 600)
        view.show()
        root_item = view.rootObject()
        root_item.setProperty("sessionSkipped", True)
        root_item.setProperty("currentIndex", 1)
        QTest.qWait(70)
        press(view, find_control(root_item, "openImportDialog"))
        dialog = find_control(root_item, "modernImportDialog")
        wait_until(lambda: bool(dialog.property("opened")))
        imports = view.rootContext().contextProperty("importBridge")
        wait_until(lambda: not imports.busy)
        imports.importMrpackFile((tmp_path / "missing.mrpack").as_uri(), "", "")
        wait_until(lambda: bool(dialog.property("failure")))
        assert "missing.mrpack" in find_control(dialog, "importStatus").property("text")
        assert dialog.property("opened")
        workspace_scroll = find_control(root_item, "instancesScroll")
        before = workspace_scroll.property("contentY")
        wheel(view, find_control(dialog, "importBodyScroll"))
        QTest.qWait(70)
        assert workspace_scroll.property("contentY") == before
        assert not launcher.list_instances()
        dialog.setProperty("section", 1)
        QTest.qWait(30)
        import_button = find_item(view.contentItem(), "importExternal-0")
        assert import_button is not None
        import_position = import_button.mapToScene(QPointF())
        assert (
            dialog.property("x")
            <= import_position.x()
            < dialog.property("x") + dialog.property("width")
        )
        press(view, import_button)
        wait_until(lambda: not imports.busy and len(launcher.list_instances()) == 1)
        imported = launcher.list_instances()[0]
        assert (
            launcher.instance_game_dir(imported) / "saves" / "level.dat"
        ).read_bytes() == b"import-world"
        assert (external / "saves" / "level.dat").read_bytes() == b"import-world"
        QTest.keyClick(view, Qt.Key.Key_Escape)
        wait_until(lambda: not dialog.property("visible"))
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
