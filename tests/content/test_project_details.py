"""Giới thiệu dự án đi qua cùng nguồn HTTP như tìm kiếm và được trả về dataclass."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.content.model import ContentSource, Project
from test_api import make_launcher


@pytest.mark.parametrize("source", ["modrinth", "curseforge"])
def test_fetch_full_project_description(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    source: ContentSource,
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            modrinth_api=server.url("/modrinth"),
            curseforge_proxy=server.url("/cf"),
        ),
    )
    project = Project(
        "123", "test-mod", "Test", "Summary", "Author", "mod", "", 0, 0, ("fabric",), source
    )
    if source == "modrinth":
        path = "/modrinth/project/123"
        body = "# Full about\nDescription"
        server_state.add(path, json.dumps({"body": body}).encode())
    else:
        path = "/cf/mods/123/description"
        body = "<h1>Full about</h1><p>Description</p>"
        server_state.add(path, json.dumps({"data": body}).encode())
    details = launcher.fetch_content_details(project)
    assert details.body == body
    assert details.body_format == ("markdown" if source == "modrinth" else "html")
    assert details.website_url.startswith("https://")
    assert server_state.request_count(path) == 1
