"""Gói Optimized: cài Fabulously Optimized đúng phiên bản; chưa có bản thì báo, không cài bừa."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from fabric_fixture import publish_fabric
from local_https_server import LocalHttpsServer, ServerState
from modpack_fixture import PACK_ID, modpack_project, publish_modpack
from modrinth_fixture import make_content_launcher
from nostalgia.errors import ContentError
from nostalgia.facade.presets import PRESET_PROJECT_IDS


def make_preset_launcher(server, state, tmp_path, certificate_pair):
    launcher = make_content_launcher(server, state, tmp_path, certificate_pair)
    publish_fabric(state)
    host = publish_modpack(server, state)
    # Gói Optimized hỏi đúng mã thật của Fabulously Optimized; máy chủ giả trả cùng danh sách bản.
    state.add(
        f"/modrinth/project/{PRESET_PROJECT_IDS['optimized']}/version",
        state.routes[f"/modrinth/project/{PACK_ID}/version"].body,
    )
    project = modpack_project()
    state.add(
        "/modrinth/projects",
        json.dumps(
            [
                {
                    "id": PACK_ID,
                    "slug": project.project_slug,
                    "title": project.title,
                    "project_type": "modpack",
                    "icon_url": "",
                    "downloads": 1,
                    "followers": 1,
                }
            ]
        ).encode(),
    )
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, fabric_meta=server.url("/fabric"))
    )
    return launcher, host


def test_optimized_preset_installs_the_pack_for_the_chosen_version(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    from fake_mojang import VERSION_ID

    launcher, host = make_preset_launcher(server, server_state, tmp_path, certificate_pair)
    assert launcher.list_preset_game_versions("optimized") == (VERSION_ID,)

    instance = launcher.install_preset(
        "optimized", "toi-uu", "Optimized", game_version=VERSION_ID, allowed_hosts=(host,)
    )
    assert instance.version_id.startswith("fabric-loader-")
    assert (launcher.paths.instance_dir("toi-uu") / "mods" / "sodium.jar").is_file()
    assert server_state.received_path("/modrinth/projects").startswith("/modrinth/projects?ids=")


def test_optimized_preset_refuses_a_version_the_pack_does_not_have(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, host = make_preset_launcher(server, server_state, tmp_path, certificate_pair)
    with pytest.raises(ContentError, match=r"chưa có bản cho Minecraft 1\.2\.5"):
        launcher.install_preset(
            "optimized", "cu", "Cũ", game_version="1.2.5", allowed_hosts=(host,)
        )
    assert launcher.list_instances() == ()
    with pytest.raises(ContentError, match="không có gói"):
        launcher.install_preset("bay", "x", "x", game_version="1.2.5")
