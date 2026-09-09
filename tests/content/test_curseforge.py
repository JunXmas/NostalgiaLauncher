"""CurseForge qua máy chủ giả đóng vai Worker/API: tham số tìm, khoá riêng đổi đường, URL CDN."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from curseforge_fixture import FILES_BODY, SEARCH_BODY
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Launcher
from nostalgia.content.curseforge import cdn_url
from nostalgia.settings.store import Settings
from test_api import make_launcher


def make_cf_launcher(
    server: LocalHttpsServer,
    state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> Launcher:
    for base in ("/proxy", "/direct"):
        state.add(f"{base}/mods/search", json.dumps(SEARCH_BODY).encode())
        state.add(f"{base}/mods/394468/files", json.dumps(FILES_BODY).encode())
    launcher = make_launcher(server, state, tmp_path, certificate_pair)
    return replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            curseforge_proxy=server.url("/proxy"),
            curseforge_direct=server.url("/direct"),
            curseforge_cdn=server.url("/cdn"),
        ),
    )


def test_search_goes_through_the_proxy_without_a_key(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_cf_launcher(server, server_state, tmp_path, certificate_pair)

    page = launcher.search_content(
        None,
        "mod",
        source="curseforge",
        query="sodium",
        sort="downloads",
        game_versions=("26.2",),
        loaders=("fabric",),
    )

    hit = page.hits[0]
    assert (hit.title, hit.author, hit.source, hit.loaders) == (
        "Sodium",
        "jellysquid3",
        "curseforge",
        ("fabric", "neoforge"),
    )
    assert page.total_hits == 7 and hit.downloads == 12345
    query = parse_qs(urlparse(server_state.received_path("/proxy/mods/search")).query)
    assert query["classId"] == ["6"] and query["gameVersion"] == ["26.2"]
    assert query["modLoaderType"] == ["4"] and query["sortField"] == ["6"]
    assert "x-api-key" not in {
        k.lower() for k in server_state.routes["/proxy/mods/search"].received_headers
    }


def test_a_private_key_switches_to_the_direct_api(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_cf_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.save_settings(Settings(curseforge_api_key="khoa-rieng"))

    launcher.search_content(None, "mod", source="curseforge")

    assert server_state.request_count("/proxy/mods/search") == 0
    assert server_state.received_header("/direct/mods/search", "x-api-key") == "khoa-rieng"


def test_files_map_to_versions_with_cdn_fallback_and_encoded_names(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_cf_launcher(server, server_state, tmp_path, certificate_pair)

    with launcher.make_http_client() as http_client:
        versions = launcher.fetch_versions(http_client, "curseforge", "394468")

    project_version = versions[0]
    assert (project_version.version_type, project_version.game_versions) == ("beta", ("26.2",))
    assert project_version.loaders == ("fabric",)
    assert project_version.file_url == server.url("/cdn/8793/729/sodium%2Bmc26.2.jar")
    assert project_version.required_project_ids == ("306612",)
    assert cdn_url(launcher.endpoints, 1234, "a b.jar").endswith("/cdn/1/234/a%20b.jar")
