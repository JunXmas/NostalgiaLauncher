"""Cầu nối nội dung qua máy chủ giả: tìm, cài, sổ, bộ lọc, thế hệ cũ bị bỏ, tải thêm nối mô hình."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import SODIUM, fabric_target, make_content_launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge

pytestmark = pytest.mark.usefixtures("qt_app")


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


def test_filters_follow_the_instance_then_widen_when_the_user_asks(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Chọn bản chơi Fabric 1.99.9 -> bộ lọc = fabric + 1.99.9; tick thêm Forge và một phiên
    bản khác -> facets gửi đi là mảng OR; bỏ hết phiên bản -> không gửi facet versions."""
    import json
    from urllib.parse import parse_qs, urlparse

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.selectInstance(target.instance_id)
    assert content_bridge.selectedLoaders == ["fabric"]
    assert content_bridge.selectedGameVersions == [VERSION_ID]

    content_bridge.setLoaderSelected("forge", True)
    content_bridge.setGameVersionSelected("1.20.1", True)
    content_bridge.search("mod", "", "downloads")
    wait_until(lambda: not content_bridge.searching)
    query = parse_qs(urlparse(server_state.received_path("/modrinth/search")).query)
    assert json.loads(query["facets"][0]) == [
        ["project_type:mod"],
        [f"versions:{VERSION_ID}", "versions:1.20.1"],
        ["categories:fabric", "categories:forge"],
    ]

    content_bridge.clearGameVersions()
    content_bridge.setLoaderSelected("fabric", False)
    content_bridge.setLoaderSelected("forge", False)
    content_bridge.search("mod", "", "downloads")
    wait_until(lambda: not content_bridge.searching)
    query = parse_qs(urlparse(server_state.received_path("/modrinth/search")).query)
    assert json.loads(query["facets"][0]) == [["project_type:mod"]]


def test_load_more_appends_to_the_model_instead_of_resetting_it(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Tải thêm phải NỐI vào mô hình (rowsInserted) chứ không reset: reset là view về đầu."""
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.selectInstance(target.instance_id)
    model = content_bridge.resultsModel
    events: list[str] = []
    model.modelReset.connect(lambda: events.append("reset"))
    model.rowsInserted.connect(lambda _parent, first, last: events.append(f"insert {first}-{last}"))

    content_bridge.search("mod", "", "downloads")
    wait_until(lambda: not content_bridge.searching and model.rowCount() == 1)
    assert events == ["reset"]
    assert content_bridge.hasMore  # máy chủ giả nói có 41 kết quả

    # Trang sau trả cùng một Sodium: không nối trùng, và không reset.
    content_bridge.loadMore()
    wait_until(lambda: not content_bridge.searching)
    assert events == ["reset"]
    assert model.rowCount() == 1
    assert model.row(0)["installed"] is False


def test_switching_source_clears_results_and_routes_to_curseforge(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Đổi nguồn thì kết quả cũ biến mất ngay và lần tìm sau đi qua đường CurseForge."""
    import json
    from dataclasses import replace

    from curseforge_fixture import SEARCH_BODY

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    server_state.add("/cf/mods/search", json.dumps(SEARCH_BODY).encode())
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, curseforge_proxy=server.url("/cf"))
    )
    target = fabric_target(launcher)
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.selectInstance(target.instance_id)
    content_bridge.search("mod", "", "downloads")
    wait_until(lambda: not content_bridge.searching and len(content_bridge.results) == 1)

    content_bridge.setSource("curseforge")
    assert content_bridge.results == []
    assert content_bridge.source == "curseforge"
    content_bridge.search("mod", "sodium", "downloads")
    wait_until(lambda: not content_bridge.searching and len(content_bridge.results) == 1)
    assert content_bridge.results[0]["source"] == "curseforge"
    assert server_state.request_count("/cf/mods/search") == 1


def test_install_modpack_creates_an_instance_and_selects_it(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Cài modpack từ thẻ: bản chơi mới xuất hiện ở bridge chính, tín hiệu mang mã bản chơi.
    Máy chủ giả là host lạ với luật mrpack, nên ở đây kiểm đúng chỗ luật đó từ chối."""
    import json
    from dataclasses import replace

    from fabric_fixture import publish_fabric
    from modpack_fixture import PACK_ID, publish_modpack

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    publish_fabric(server_state)
    publish_modpack(server, server_state)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, fabric_meta=server.url("/fabric"))
    )
    server_state.add(
        "/modrinth/search",
        json.dumps(
            {
                "hits": [{"project_id": PACK_ID, "title": "Gói Vui", "project_type": "modpack"}],
                "offset": 0,
                "total_hits": 1,
            }
        ).encode(),
    )
    main_bridge = LauncherBridge(launcher)
    content_bridge = ContentBridge(launcher, main_bridge)
    failures: list[str] = []
    content_bridge.failed.connect(failures.append)
    content_bridge.search("modpack", "", "relevance")
    wait_until(lambda: not content_bridge.searching and len(content_bridge.results) == 1)
    assert content_bridge.results[0]["contentKind"] == "modpack"

    content_bridge.install(PACK_ID)  # đường cài thường phải từ chối modpack, im lặng
    assert content_bridge.results[0]["installing"] is False

    content_bridge.installModpack(PACK_ID, "")
    wait_until(lambda: not content_bridge.busy)
    assert failures and "host không được phép" in failures[0]
    assert main_bridge.instances == [], "bị từ chối thì không được tạo bản chơi dở"
