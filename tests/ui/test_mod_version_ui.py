"""Bấm Phiên bản trong QML thật, thay mod qua HTTPS và hoàn tác bằng bản sao lưu."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until

from local_https_server import LocalHttpsServer, ServerState
from mod_version_fixture import releases
from modrinth_fixture import fabric_target, make_content_launcher
from nostalgia.ui.window import open_window
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control, press


@pytest.mark.usefixtures("qt_app")
def test_installed_mod_can_change_version_and_undo_from_the_dialog(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    target = fabric_target(launcher)
    project = launcher.search_content(target, "mod").hits[0]
    releases(server, server_state)
    launcher.install_content(target, project, version_id="old")
    warnings: list[str] = []
    previous = qInstallMessageHandler(lambda _level, _context, message: warnings.append(message))
    view, bridge = open_window(launcher)
    content: Any = view.rootContext().contextProperty("contentBridge")
    versions: Any = view.rootContext().contextProperty("modVersionBridge")
    try:
        assert not view.errors(), warnings
        root_item = view.rootObject()
        assert root_item is not None
        root_item.setProperty("sessionSkipped", True)
        view.show()
        view.requestActivate()
        content.selectInstance(target.instance_id)
        root_item.setProperty("currentIndex", 2)
        QTest.qWait(100)
        press(view, find_control(root_item, "openModernInstalled"))
        wait_until(lambda: bool(content.installed) and not content.identifying)
        press(view, find_control(root_item, "installedVersions-sodium-old.jar"))
        dialog = find_control(root_item, "modVersionDialog")
        wait_until(lambda: dialog.property("opened") and not versions.busy)
        assert not find_control(root_item, "modVersion-old").property("clickable")
        choose = find_control(root_item, "modVersion-new")
        assert choose.property("clickable")
        assert view.grabWindow().save(str(tmp_path / "mod-version-choices.png"))
        bridge.setStorageBusy(True)
        versions.apply("new")
        assert launcher.list_installed_content(target, "mod")[0].version_id == "old"
        bridge.setStorageBusy(False)
        press(view, choose)
        wait_until(lambda: not versions.busy and versions._current_id == "new")
        assert launcher.list_installed_content(target, "mod")[0].version_id == "new"
        assert versions.details["canUndo"]
        assert view.grabWindow().save(str(tmp_path / "mod-version-applied.png"))
        wait_until(lambda: not content.identifying)
        press(view, find_control(root_item, "modVersionUndo"))
        wait_until(lambda: not versions.busy and not dialog.property("opened"))
        assert launcher.list_installed_content(target, "mod")[0].version_id == "old"
        assert not warnings, "\n".join(warnings)
    finally:
        view.rootContext().contextProperty("socialBridge").shutdown()
        view.rootContext().contextProperty("multiplayerBridge").shutdown()
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(previous)
