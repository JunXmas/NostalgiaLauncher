"""Ba cầu nối QML ↔ lõi, qua máy chủ giả: kết quả cũ không đè kết quả mới, cài xong sổ cập
nhật, tạo bản chơi ra đúng mã. Chờ luồng nền bằng vòng processEvents có hạn — không ngủ mù."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import SODIUM, fabric_target, make_content_launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import CatalogBridge, slugify
from nostalgia.ui.content_bridge import ContentBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def wait_until(condition: Callable[[], bool], seconds: float = 10.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QGuiApplication.processEvents()
        if condition():
            return
        time.sleep(0.01)
    message = "luồng nền không xong trong thời hạn"
    raise AssertionError(message)


def test_content_bridge_searches_installs_and_lists(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    main_bridge = LauncherBridge(launcher)
    content_bridge = ContentBridge(launcher, main_bridge)
    failures: list[str] = []
    content_bridge.failed.connect(failures.append)

    content_bridge.selectInstance(target.instance_id)
    assert (content_bridge.gameVersion, content_bridge.loaderKind) == (VERSION_ID, "fabric")

    content_bridge.search("mod", "sodium", "downloads")
    wait_until(lambda: not content_bridge.searching and len(content_bridge.results) == 1)
    assert content_bridge.results[0]["title"] == "Sodium"
    assert content_bridge.results[0]["installed"] is False
    assert content_bridge.hasMore is True

    content_bridge.install(SODIUM)
    assert content_bridge.results[0]["installing"] is True
    wait_until(lambda: not content_bridge.busy)
    assert content_bridge.results[0]["installed"] is True
    assert content_bridge.results[0]["installing"] is False

    content_bridge.refreshInstalled("mod")
    names = sorted(row["fileName"] for row in content_bridge.installed)
    assert names == ["AANobbMI.jar", "P7dR8mSH.jar"]

    content_bridge.setEnabled("mod", "AANobbMI.jar", False)
    assert (
        next(row for row in content_bridge.installed if row["fileName"] == "AANobbMI.jar")[
            "enabled"
        ]
        is False
    )
    content_bridge.remove("mod", "P7dR8mSH.jar")
    assert [row["fileName"] for row in content_bridge.installed] == ["AANobbMI.jar"]
    assert failures == []


def test_stale_search_results_are_dropped(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Hai lần tìm liên tiếp: chỉ thế hệ sau được ghi, dù thế hệ trước về muộn."""
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.selectInstance(target.instance_id)

    first = content_bridge.next_generation()
    content_bridge.search("mod", "a", "relevance")
    content_bridge.search("mod", "b", "relevance")
    assert not content_bridge.is_current(first)
    wait_until(lambda: not content_bridge.searching)
    # Cả hai đều trả cùng một Sodium: không được nhân đôi.
    assert len(content_bridge.results) == 1


def test_catalog_bridge_creates_a_vanilla_instance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    main_bridge = LauncherBridge(launcher)
    catalog_bridge = CatalogBridge(launcher, main_bridge)
    created: list[str] = []
    catalog_bridge.created.connect(created.append)

    catalog_bridge.loadReleasedVersions()
    wait_until(lambda: len(catalog_bridge.releasedVersions) == 1)
    assert catalog_bridge.releasedVersions[0] == {"versionId": VERSION_ID, "major": "1.99"}

    catalog_bridge.createInstance("Sinh tồn vui!", VERSION_ID, "vanilla", "", 2048)
    wait_until(lambda: bool(created))
    assert created == ["sinh-ton-vui"]
    instance = launcher.list_instances()[0]
    assert (instance.display_name, instance.max_heap_megabytes) == ("Sinh tồn vui!", 2048)
    assert launcher.list_installed_versions() == (VERSION_ID,)


def test_slugify_is_safe_and_unique() -> None:
    assert slugify("Sinh tồn vui!", set()) == "sinh-ton-vui"
    assert slugify("Sinh tồn vui!", {"sinh-ton-vui"}) == "sinh-ton-vui-2"
    assert slugify("...", set()) == "ban-choi"
    assert slugify("-bat-dau-gach", set()) == "bat-dau-gach"
    assert slugify("日本語", set()) == "ban-choi"
