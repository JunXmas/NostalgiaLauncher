"""Danh sách lớn dựng số delegate hữu hạn, cuộn tới cuối và thao tác đúng file."""

from collections.abc import Iterator
from typing import Any, cast

import pytest
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_instance_library import prepare
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.api import Launcher
from nostalgia.content.model import Project, SearchPage
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


def visuals(node: QQuickItem) -> Iterator[QQuickItem]:
    yield node
    for child in node.childItems():
        yield from visuals(child)


def test_large_library_keeps_delegates_bounded_and_reaches_last_project(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, view, _bridge, root_item = preview
    projects = tuple(
        Project(
            f"demo-{position}",
            f"demo-{position}",
            f"Mod {position}",
            "About",
            "Author",
            "modpack",
            "",
            100,
            1,
            ("fabric",),
        )
        for position in range(2000)
    )
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage(projects, 0, 2000))
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 2)
    content = view.rootContext().contextProperty("contentBridge")
    wait_until(lambda: not content.searching and len(content.results) == 2000)
    scroll = find_control(root_item, "libraryScroll")
    wait_until(lambda: scroll.property("count") == 2000)
    QTest.qWait(100)
    assert sum(n.objectName().startswith("projectCard-") for n in visuals(root_item)) < 60
    scroll.scrollBy(float(scroll.property("maxY")), True)
    wait_until(lambda: find_item(root_item, "projectCard-demo-1999") is not None)
    assert sum(n.objectName().startswith("projectCard-") for n in visuals(root_item)) < 60
    scroll.scrollBy(-1000000, True)
    wait_until(lambda: find_item(root_item, "projectCard-demo-0") is not None)
    assert content.results[0]["projectId"] == "demo-0"


def test_large_installed_list_keeps_position_and_reuses_correct_remove_state(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, view, _bridge, root_item = preview
    prepare(preview, monkeypatch)
    content = cast(Any, view.rootContext().contextProperty("contentBridge"))
    wait_until(lambda: not content.busy and not content.identifying)
    rows = [
        {
            "fileName": f"mod-{position:04d}.jar",
            "label": f"Mod {position}",
            "enabled": True,
            "projectId": "",
            "source": "manual",
            "contentKind": "mod",
            "fileSize": 100,
            "iconUrl": "",
            "versionNumber": "1",
            "latestVersion": "",
        }
        for position in range(2000)
    ]
    content._installed_rows = rows
    content._installed_model.sync(rows)
    content.installedChanged.emit()
    scope = find_control(root_item, "modernInstanceManager").property("contentItem")
    scroll = find_control(root_item, "installedScroll")
    wait_until(lambda: scroll.property("count") == 2000)
    QTest.qWait(100)
    assert sum(n.objectName().startswith("installedCard-") for n in visuals(scope)) < 30
    first = find_item(scope, "installedCard-mod-0000.jar")
    assert first is not None
    first.setProperty("confirmingRemove", True)
    scroll.scrollBy(float(scroll.property("maxY")), True)
    wait_until(lambda: find_item(scope, "installedCard-mod-1999.jar") is not None)
    last = find_item(scope, "installedCard-mod-1999.jar")
    assert last is not None and not last.property("confirmingRemove")
    at_end = float(scroll.property("contentY"))
    rows[-1]["enabled"] = False
    content._installed_model.sync(rows)
    content.installedChanged.emit()
    QTest.qWait(100)
    assert float(scroll.property("contentY")) == pytest.approx(at_end)
    assert not last.property("installedContent").property("enabled")
    assert sum(n.objectName().startswith("installedCard-") for n in visuals(scope)) < 30
