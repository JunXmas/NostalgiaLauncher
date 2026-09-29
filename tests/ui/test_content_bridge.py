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


def test_modpack_kind_drops_the_filters_inherited_from_the_target_instance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Phản hồi người chơi: tìm modpack thì kho bị lọc mất gần hết vì bộ lọc còn ghim phiên
    bản của bản chơi đang chọn. Modpack TẠO RA bản chơi mới nên nó không thuộc phiên bản nào
    — chuyển sang chip Modpack là bộ lọc thừa hưởng phải rơi đi, và quay lại Mod thì có lại.
    """
    import json
    from urllib.parse import parse_qs, urlparse

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.selectInstance(target.instance_id)
    assert content_bridge.selectedGameVersions == [VERSION_ID]

    content_bridge.setKind("modpack")

    assert content_bridge.selectedGameVersions == []
    assert content_bridge.selectedLoaders == []
    content_bridge.search("modpack", "", "downloads")
    wait_until(lambda: not content_bridge.searching)
    query = parse_qs(urlparse(server_state.received_path("/modrinth/search")).query)
    assert json.loads(query["facets"][0]) == [["project_type:modpack"]]

    content_bridge.setKind("mod")

    assert content_bridge.selectedGameVersions == [VERSION_ID]
    assert content_bridge.selectedLoaders == ["fabric"]


def test_a_filter_the_user_set_by_hand_survives_switching_kinds(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Mặt sau của luật trên: chỉ bộ lọc MẶC ĐỊNH mới được đặt lại. Người dùng tự tick 1.7.10
    rồi đổi chip thì cái tick đó phải còn — nếu không, đổi chip là mất việc vừa làm."""
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.selectInstance(target.instance_id)

    content_bridge.clearGameVersions()
    content_bridge.setGameVersionSelected("1.7.10", True)
    content_bridge.setKind("modpack")

    assert content_bridge.selectedGameVersions == ["1.7.10"]


def test_clearing_loaders_widens_the_search_to_every_loader(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Ô lọc có dấu ✕ xoá cả nhóm; không có nó người dùng phải bỏ tick từng mục."""
    import json
    from urllib.parse import parse_qs, urlparse

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    content_bridge = ContentBridge(launcher, LauncherBridge(launcher))
    content_bridge.selectInstance(target.instance_id)
    assert content_bridge.selectedLoaders == ["fabric"]

    content_bridge.clearLoaders()
    content_bridge.clearGameVersions()
    content_bridge.search("mod", "", "downloads")
    wait_until(lambda: not content_bridge.searching)

    query = parse_qs(urlparse(server_state.received_path("/modrinth/search")).query)
    assert json.loads(query["facets"][0]) == [["project_type:mod"]]
