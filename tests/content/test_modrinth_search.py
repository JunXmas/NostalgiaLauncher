"""Tìm kiếm Modrinth qua máy chủ giả: facets, sắp xếp, User-Agent, luật chọn bản."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import (
    fabric_target,
    make_content_launcher,
)
from nostalgia.api import Instance
from nostalgia.content.model import ProjectVersion
from nostalgia.content.modrinth import choose_version


def test_search_sends_project_type_version_and_loader_facets(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    assert (target.game_version, target.loader_kind) == (VERSION_ID, "fabric")

    page = launcher.search_content(target, "mod", query="sodium", sort="downloads", offset=0)

    assert [hit.title for hit in page.hits] == ["Sodium"]
    assert page.hits[0].loaders == ("fabric",)
    assert page.total_hits == 41 and page.has_more
    query = parse_qs(urlparse(server_state.received_path("/modrinth/search")).query)
    assert json.loads(query["facets"][0]) == [
        ["project_type:mod"],
        [f"versions:{VERSION_ID}"],
        ["categories:fabric"],
    ]
    assert query["index"] == ["downloads"] and query["query"] == ["sodium"]
    assert server_state.received_header("/modrinth/search", "User-Agent").startswith(
        "NostalgiaLauncher/"
    )


def test_resourcepack_search_does_not_filter_by_loader(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)

    launcher.search_content(target, "resourcepack")

    query = parse_qs(urlparse(server_state.received_path("/modrinth/search")).query)
    assert json.loads(query["facets"][0]) == [
        ["project_type:resourcepack"],
        [f"versions:{VERSION_ID}"],
    ]


def test_choose_version_rules() -> None:
    def make(loaders: tuple[str, ...], games: tuple[str, ...], kind_type: str) -> ProjectVersion:
        return ProjectVersion(
            version_id=kind_type,
            project_id="p",
            version_number="1",
            version_type=kind_type,
            game_versions=games,
            loaders=loaders,
            date_published="",
            file_url="u",
            file_name="f.jar",
            file_sha1="0" * 40,
            file_size=1,
            required_project_ids=(),
        )

    beta = make(("fabric",), ("1.20.1",), "beta")
    release_old_game = make(("fabric",), ("1.19.4",), "release")
    forge = make(("forge",), ("1.20.1",), "release")
    shader = make(("iris",), ("1.20.1",), "release")

    assert (
        choose_version(
            (beta, release_old_game, forge),
            game_version="1.20.1",
            loader_kind="fabric",
            content_kind="mod",
        )
        is beta
    )
    assert (
        choose_version((forge,), game_version="1.20.1", loader_kind="fabric", content_kind="mod")
        is None
    )
    # Shader không quan tâm loader của bản chơi.
    assert (
        choose_version(
            (shader,), game_version="1.20.1", loader_kind="vanilla", content_kind="shader"
        )
        is shader
    )


def test_target_loader_is_read_from_the_version_id_for_every_loader(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Lỗi thật đã gặp: bản Forge bị coi là vanilla nên thư viện chặn cài mod. Giờ mọi loader
    đều nhận ra từ mã bản, và bản Quilt tìm mod với facets fabric + quilt."""
    from nostalgia.storage.files import atomic_write_json

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_version(VERSION_ID)
    for version_id, main_class in (
        (f"{VERSION_ID}-forge-47.4.10", "cpw.mods.bootstraplauncher.BootstrapLauncher"),
        (f"neoforge-{VERSION_ID}", "cpw.mods.bootstraplauncher.BootstrapLauncher"),
        (f"quilt-loader-0.29.1-{VERSION_ID}", "org.quiltmc.loader.impl.launch.knot.KnotClient"),
    ):
        atomic_write_json(
            launcher.paths.version_json(version_id),
            {"id": version_id, "inheritsFrom": VERSION_ID, "mainClass": main_class},
        )
        launcher.create_instance(Instance(instance_id=version_id[:8], version_id=version_id))

    forge = launcher.describe_content_target(f"{VERSION_ID}-forge-47.4.10"[:8])
    neoforge = launcher.describe_content_target(f"neoforge-{VERSION_ID}"[:8])
    quilt = launcher.describe_content_target("quilt-lo")
    assert (forge.loader_kind, neoforge.loader_kind, quilt.loader_kind) == (
        "forge",
        "neoforge",
        "quilt",
    )

    launcher.search_content(quilt, "mod")
    query = parse_qs(urlparse(server_state.received_path("/modrinth/search")).query)
    assert json.loads(query["facets"][0])[2] == ["categories:quilt", "categories:fabric"]
