"""Native Qt preview of server configuration, library, console and layered confirmations."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QObject, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until

from nostalgia.ui.preview import open_preview
from nostalgia.ui.server_controller import ServerController
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control, press
from server_fixture import ServerAccountFixture, fake_java, server_launcher

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def server_view(tmp_path: Path) -> Iterator[tuple[QQuickView, QObject, ServerController, str]]:
    launcher, _http_client = server_launcher(tmp_path)
    account = ServerAccountFixture()
    manager = launcher.make_server_manager(account)
    server = manager.install("Thế giới cùng bạn", "paper", "1.21.1", "132")
    manager.save_settings(
        server.server_id, manager.properties(server.server_id), 2048, str(fake_java(tmp_path))
    )
    view, _bridge = open_preview(launcher, server_gateway=account)
    root_item = view.rootObject()
    assert root_item is not None
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)
    view.show()
    QTest.qWait(300)
    press(view, find_control(root_item, "workspaceServers"))
    wait_until(lambda: root_item.findChild(QObject, "dedicatedServers") is not None)
    servers = view.rootContext().contextProperty("serverBridge")
    assert isinstance(servers, ServerController)
    servers.checkAccess()
    wait_until(lambda: bool(servers.property("hasAccess")) and not servers.busy)
    yield view, root_item, servers, server.server_id
    servers.shutdown()
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def test_settings_save_real_properties_and_console_saves_world(
    server_view: tuple[Any, ...],
) -> None:
    view, root_item, servers, server_id = server_view
    press(view, find_item(root_item, "serverManage-" + server_id))
    manager = find_control(root_item, "serverManagerDialog")
    wait_until(
        lambda: (
            manager.property("opened")
            and servers.property("selected").get("server_id") == server_id
            and not servers.busy
        )
    )
    content_item = manager.property("contentItem")
    heap = find_control(root_item, "serverHeap")
    heap.setProperty("text", "4096")
    players = find_item(content_item, "serverProperty-max-players")
    assert players is not None
    players.setProperty("text", "12")
    eula = find_control(root_item, "serverEula")
    eula.toggled.emit(True)
    press(view, find_control(root_item, "serverSettingsSave"))
    wait_until(
        lambda: not servers.busy and servers.domain_manager.server(server_id).heap_megabytes == 4096
    )
    assert dict(servers.domain_manager.properties(server_id).values)["max-players"] == "12"
    press(view, find_item(content_item, "serverSection-2"))
    press(view, find_control(root_item, "serverStart"))
    wait_until(lambda: servers.domain_manager.ready_id == server_id and not servers.busy)
    field = find_control(root_item, "serverCommand")
    field.setProperty("text", "say Chào mọi người")
    press(view, find_control(root_item, "serverCommandSend"))
    wait_until(lambda: not servers.busy)
    press(view, find_control(root_item, "serverStart"))
    wait_until(lambda: not servers.busy and not servers.domain_manager.running_id)
    assert (servers.domain_manager.directory(server_id) / "saved-world.txt").is_file()


def test_server_confirm_stacks_correctly_and_small_window_scrolls(
    server_view: tuple[Any, ...],
) -> None:
    view, root_item, servers, server_id = server_view
    warnings: list[str] = []
    previous = qInstallMessageHandler(lambda _mode, _context, message: warnings.append(message))
    try:
        press(view, find_item(root_item, "serverManage-" + server_id))
        manager = find_control(root_item, "serverManagerDialog")
        wait_until(lambda: manager.property("opened") and not servers.busy)
        press(view, find_item(manager.property("contentItem"), "serverSection-3"))
        press(view, find_control(root_item, "serverTrash"))
        confirm = find_control(root_item, "confirmationModal")
        wait_until(lambda: bool(confirm.property("opened")))
        assert confirm.property("z") > manager.property("z")
        press(view, find_control(root_item, "confirmCancel"))
        assert manager.property("opened")
        press(view, find_item(manager.property("contentItem"), "serverSection-0"))
        view.resize(1024, 600)
        view.rootContext().contextProperty("settingsBridge").setAppearance(
            150, False, False, True, "vi"
        )
        QTest.qWait(300)
        scroll = find_control(root_item, "serverSettingsScroll")
        assert scroll.property("height") > 100 and scroll.property("maxY") > 0
        assert manager.property("width") <= view.width() - 35
        manager.close()
        press(view, find_control(root_item, "createModernInstance"))
        create = find_control(root_item, "serverCreateDialog")
        wait_until(lambda: bool(create.property("opened")))
        assert create.property("height") < view.height()
        assert find_control(root_item, "serverCreateScroll").property("maxY") > 0
    finally:
        qInstallMessageHandler(previous)
    assert not [
        message
        for message in warnings
        if any(
            term in message
            for term in ("qml:", ".qml:", "ReferenceError", "TypeError", "binding loop")
        )
    ]


def test_library_opens_centered_version_picker_and_installs_real_jar(
    server_view: tuple[Any, ...],
) -> None:
    view, root_item, servers, server_id = server_view
    press(view, find_item(root_item, "serverManage-" + server_id))
    manager = find_control(root_item, "serverManagerDialog")
    wait_until(
        lambda: manager.property("opened") and not servers.busy and manager.property("ready")
    )
    press(view, find_item(manager.property("contentItem"), "serverSection-1"))
    press(view, find_control(root_item, "serverContentSearch"))
    wait_until(lambda: len(servers.property("projects")) == 3 and not servers.busy)
    project_button = find_item(manager.property("contentItem"), "serverProject-luckperms")
    assert project_button is not None
    assert project_button.property("width") > 100
    assert project_button.parentItem().property("width") > 400
    press(view, project_button)
    picker = find_control(root_item, "serverContentVersionDialog")
    wait_until(
        lambda: (
            picker.property("opened")
            and len(servers.property("contentVersions")) == 1
            and not servers.busy
        )
    )
    assert abs(picker.property("x") + picker.property("width") / 2 - view.width() / 2) < 2
    select = find_control(root_item, "serverContentVersion")
    press(view, select, Qt.Key.Key_Space)
    QTest.keyClick(view, Qt.Key.Key_Down)
    QTest.keyClick(view, Qt.Key.Key_Return)
    QTest.qWait(50)
    press(view, find_control(root_item, "serverContentInstall"))
    wait_until(lambda: not servers.busy and not picker.property("visible"))
    assert (servers.domain_manager.directory(server_id) / "plugins" / "luckperms.jar").is_file()
