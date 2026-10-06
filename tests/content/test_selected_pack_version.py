"""Modpack chỉ định phải lấy đúng archive; metadata không khớp không được tạo bản chơi."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from fabric_fixture import publish_fabric
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modpack_fixture import PACK_ID, modpack_project, publish_modpack
from modrinth_fixture import version_document
from nostalgia.errors import ContentError
from test_api import make_launcher


@pytest.mark.parametrize("selected_id", ["old", "missing", "wrong-game", "mislabeled"])
def test_install_selected_pack_archive(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    selected_id: str,
) -> None:
    host = publish_modpack(server, server_state)
    publish_fabric(server_state)
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            fabric_meta=server.url("/fabric"),
            modrinth_api=server.url("/modrinth"),
        ),
    )
    documents = []
    server_state.add("/missing-latest.mrpack", b"missing", status=404)
    # Use the existing fixture archive for the old release; latest deliberately points
    # to a missing file so choosing the wrong release cannot accidentally pass.
    from nostalgia.content import modrinth

    with launcher.make_http_client() as http_client:
        published = modrinth.fetch_project_versions(
            http_client, PACK_ID, endpoints=launcher.endpoints
        )[0]
    for version_id in ("new", "old", "wrong-game", "mislabeled"):
        document = version_document(PACK_ID, loaders=["fabric"], url=published.file_url)
        document["id"] = version_id
        files = cast(list[dict[str, Any]], document["files"])
        files[0]["filename"] = "pack.mrpack"
        files[0]["hashes"]["sha1"] = published.file_sha1
        if version_id == "new":
            files[0]["url"] = server.url("/missing-latest.mrpack")
        if version_id in ("wrong-game", "mislabeled"):
            document["game_versions"] = ["1.20.1"]
        documents.append(document)
    server_state.add(f"/modrinth/project/{PACK_ID}/version", json.dumps(documents).encode())
    if selected_id == "old":
        instance = launcher.install_modpack(
            modpack_project(),
            "selected",
            version_id=selected_id,
            game_version=VERSION_ID,
            allowed_hosts=(host,),
        )
        assert instance.instance_id == "selected"
        assert (launcher.instance_game_dir(instance) / "config" / "goi.toml").is_file()
    else:
        with pytest.raises(ContentError):
            launcher.install_modpack(
                modpack_project(),
                "selected",
                version_id=selected_id,
                game_version="1.20.1" if selected_id == "mislabeled" else VERSION_ID,
                allowed_hosts=(host,),
            )
        assert not launcher.list_instances()
    assert server_state.request_count("/missing-latest.mrpack") == 0
