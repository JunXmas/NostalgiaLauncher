"""Kéo thả Qt thật trên mọi trang/popup; không chép trước khi người chơi xác nhận."""

from pathlib import Path
from typing import Any, cast
from zipfile import ZipFile

import pytest
from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.instance.model import Instance
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def prepare(context: Preview, tmp_path: Path) -> tuple[Path, Path]:
    launcher, _view, bridge, root_item = context
    for instance_id in ("selected", "other"):
        launcher.create_instance(Instance(instance_id, "1.20.1"))
    bridge.announce_instances_changed()
    root_item.setProperty("sessionSkipped", True)
    first, second = tmp_path / "a.jar", tmp_path / "b.JAR"
    for path in (first, second):
        with ZipFile(path, "w") as archive:
            archive.writestr("fabric.mod.json", '{"id":"example","version":"1"}')
    return first, second


def drop(context: Preview, paths: tuple[Path, ...], *, move_only: bool = False) -> QDropEvent:
    _launcher, view, _bridge, _root_item = context
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths])
    action = Qt.DropAction.MoveAction if move_only else Qt.DropAction.CopyAction
    enter = QDragEnterEvent(
        QPoint(700, 400), action, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    )
    QGuiApplication.sendEvent(view, enter)
    event = QDropEvent(
        QPoint(700, 400), action, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
    )
    QGuiApplication.sendEvent(view, event)
    QGuiApplication.processEvents()
    assert enter.isAccepted() == event.isAccepted()
    return event


@pytest.mark.parametrize("page_index", [0, 1, 3, 6])
def test_drop_from_any_page_waits_for_instance_and_confirmation(
    preview: Preview, tmp_path: Path, page_index: int
) -> None:
    launcher, view, _bridge, root_item = preview
    sources = prepare(preview, tmp_path)
    root_item.setProperty("currentIndex", page_index)
    QTest.qWait(100)
    event = drop(preview, sources)
    assert event.isAccepted() and event.dropAction() == Qt.DropAction.CopyAction
    dialog = find_control(root_item, "localModDialog")
    wait_until(lambda: dialog.property("opened"))
    assert dialog.property("instanceId") == ""
    install = find_control(root_item, "localModInstall")
    assert not install.property("clickable")
    assert not (launcher.paths.instance_dir("selected") / "mods").exists()
    press(view, find_control(root_item, "localModCancel"))
    wait_until(lambda: not dialog.property("opened"))
    assert not (launcher.paths.instance_dir("selected") / "mods").exists()
    assert all(path.is_file() for path in sources)


def test_drop_above_existing_popup_keeps_form_help_and_installs_only_selected_instance(
    preview: Preview, tmp_path: Path
) -> None:
    launcher, view, _bridge, root_item = preview
    sources = prepare(preview, tmp_path)
    root_item.setProperty("currentIndex", 1)
    imports = find_control(root_item, "modernImportDialog")
    imports.openDialog()
    wait_until(lambda: imports.property("opened"))
    imports.setProperty("section", 1)
    drop(preview, sources)
    dialog = find_control(root_item, "localModDialog")
    wait_until(lambda: dialog.property("opened"))
    assert dialog.property("z") > imports.property("z")
    press(view, find_control(root_item, "guideButton-drop"))
    guide = find_control(root_item, "guideDialog")
    wait_until(lambda: guide.property("opened"))
    assert guide.property("z") > dialog.property("z")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: not guide.property("opened"))
    assert dialog.property("opened") and imports.property("section") == 1
    picker = find_control(root_item, "localModInstance")
    index = next(
        i for i, row in enumerate(cast(Any, _bridge).instances) if row["instanceId"] == "selected"
    )
    picker.activated.emit(index)
    assert dialog.property("instanceId") == "selected"
    press(view, find_control(root_item, "localModInstall"))
    local_bridge = view.rootContext().contextProperty("localModBridge")
    wait_until(lambda: local_bridge.details["done"] and not local_bridge.busy)
    destination = launcher.paths.instance_dir("selected") / "mods"
    assert (destination / "a.jar").read_bytes() == sources[0].read_bytes()
    assert (destination / "b.jar").read_bytes() == sources[1].read_bytes()
    assert not (launcher.paths.instance_dir("other") / "mods").exists()
    assert not _bridge.storageBusy and imports.property("opened")


def test_busy_and_game_guard_prevent_install_even_from_programmatic_slot(
    preview: Preview, tmp_path: Path
) -> None:
    launcher, view, bridge, root_item = preview
    sources = prepare(preview, tmp_path)
    drop(preview, sources)
    dialog = find_control(root_item, "localModDialog")
    dialog.setProperty("instanceId", "selected")
    local_bridge = view.rootContext().contextProperty("localModBridge")
    for gate in ("storage", "game"):
        if gate == "storage":
            bridge.setStorageBusy(True)
        else:
            bridge._game_running = True
            bridge.gameRunningChanged.emit()
        assert not find_control(root_item, "localModInstall").property("clickable")
        local_bridge.install("selected", False)
        QTest.qWait(50)
        assert not local_bridge.busy
        assert not (launcher.paths.instance_dir("selected") / "mods").exists()
        bridge.setStorageBusy(False)
        bridge._game_running = False
        bridge.gameRunningChanged.emit()


def test_invalid_jar_shows_error_preserves_selection_and_releases_storage(
    preview: Preview, tmp_path: Path
) -> None:
    launcher, view, bridge, root_item = preview
    sources = prepare(preview, tmp_path)
    bad = tmp_path / "invalid.jar"
    bad.write_text("broken")
    drop(preview, (*sources, bad))
    dialog = find_control(root_item, "localModDialog")
    dialog.setProperty("instanceId", "selected")
    press(view, find_control(root_item, "localModInstall"))
    local_bridge = view.rootContext().contextProperty("localModBridge")
    wait_until(lambda: bool(local_bridge.details["note"]) and not local_bridge.busy)
    assert not bridge.storageBusy and not local_bridge.details["done"]
    assert "JAR hợp lệ" in local_bridge.details["note"]
    assert dialog.property("instanceId") == "selected" and local_bridge.details["count"] == 3
    assert not (launcher.paths.instance_dir("selected") / "mods").exists()


def test_move_only_drop_is_ignored_and_sources_remain(preview: Preview, tmp_path: Path) -> None:
    sources = prepare(preview, tmp_path)
    assert not drop(preview, sources, move_only=True).isAccepted()
    assert not find_control(preview[3], "localModDialog").property("opened")
    assert all(path.is_file() for path in sources)
