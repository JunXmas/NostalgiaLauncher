"""Server library loads on entry; visible delete action preserves the world in trash."""

from typing import Any

import pytest
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_server_manager import server_view as server_view

from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_library_loads_once_on_entry_and_again_after_switching_source(
    server_view: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    view, root_item, servers, server_id = server_view
    calls: list[str] = []
    manager_type = type(servers.domain_manager)
    original = manager_type.search_content

    def search(manager: Any, selected_id: str, source: str, content_kind: str, query: str) -> Any:
        calls.append(source)
        return original(manager, selected_id, source, content_kind, query)

    monkeypatch.setattr(manager_type, "search_content", search)
    press(view, find_item(root_item, "serverManage-" + server_id))
    modal = find_control(root_item, "serverManagerDialog")
    wait_until(lambda: modal.property("opened") and modal.property("ready") and not servers.busy)
    assert calls == []
    press(view, find_item(modal.property("contentItem"), "serverSection-1"))
    wait_until(lambda: len(servers.property("projects")) == 3 and not servers.busy)
    assert calls == ["modrinth"]
    press(view, find_item(modal.property("contentItem"), "serverSection-0"))
    press(view, find_item(modal.property("contentItem"), "serverSection-1"))
    QTest.qWait(200)
    assert calls == ["modrinth"]
    panel = find_control(root_item, "serverContentPanel")
    panel.setProperty("source", "hangar")
    wait_until(
        lambda: (
            calls == ["modrinth", "hangar"]
            and not servers.busy
            and not servers.property("projects")
        )
    )
    assert not servers.property("projects")


def test_visible_delete_confirms_then_keeps_world_in_trash(server_view: tuple[Any, ...]) -> None:
    view, root_item, servers, server_id = server_view
    directory = servers.domain_manager.directory(server_id)
    world = directory / "world"
    world.mkdir()
    (world / "level.dat").write_bytes(b"world fixture")
    press(view, find_item(root_item, "serverDelete-" + server_id))
    modal = find_control(root_item, "confirmationModal")
    wait_until(lambda: modal.property("opened"))
    press(view, find_control(root_item, "confirmCancel"))
    assert directory.is_dir() and (world / "level.dat").read_bytes() == b"world fixture"
    press(view, find_item(root_item, "serverDelete-" + server_id))
    wait_until(lambda: modal.property("opened"))
    press(view, find_control(root_item, "confirmAccept"))
    wait_until(lambda: not servers.busy and not servers.property("servers"))
    assert not directory.exists()
    saved_worlds = list(directory.parent.glob(".trash/**/level.dat"))
    assert len(saved_worlds) == 1 and saved_worlds[0].read_bytes() == b"world fixture"
