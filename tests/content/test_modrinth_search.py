"""Tìm kiếm Modrinth qua máy chủ giả: facets, sắp xếp, User-Agent, luật chọn bản."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from modrinth_fixture import (
    fabric_target,
    make_content_launcher,
)

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
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
