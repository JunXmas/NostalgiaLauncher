"""Server library prevents client-only/wrong-loader jars and commits dependencies as a batch."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from nostalgia.errors import IntegrityError, ServerError
from nostalgia.model.json_value import as_list, as_mapping
from server_fixture import ServerAccountFixture, server_launcher
from server_http_fixture import jar_bytes


def test_plugins_are_filtered_for_platform_and_folia_requires_jar_declaration(
    tmp_path: Path,
) -> None:
    launcher, http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Folia", "folia", "1.21.1", "132")
    manager.search_content(server.server_id, "modrinth", "plugin", "permissions")
    facets = json.loads(parse_qs(urlsplit(http_client.requests[-1]).query)["facets"][0])
    assert ["categories:folia"] in facets and ["versions:1.21.1"] in facets
    assert "categories:paper" not in str(facets)
    http_client.payload = jar_bytes(folia=False)
    with pytest.raises(ServerError, match="folia-supported"):
        manager.install_content(server.server_id, "modrinth", "plugin", "luckperms", "luckperms-v1")
    assert manager.installed_content(server.server_id) == ()
    http_client.payload = jar_bytes(folia=True)
    manager.install_content(server.server_id, "modrinth", "plugin", "luckperms", "luckperms-v1")
    assert manager.installed_content(server.server_id)[0].file_name == "luckperms.jar"


def test_wrong_game_loader_and_client_only_mods_cannot_install(tmp_path: Path) -> None:
    launcher, http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Fabric", "fabric", "1.21.1", "0.16.14")
    with pytest.raises(ServerError):
        manager.content_versions(server.server_id, "modrinth", "plugin", "luckperms")
    http_client.overrides["https://api.modrinth.com/v2/project/voice"] = {
        "project_type": "mod",
        "server_side": "unsupported",
    }
    with pytest.raises(ServerError, match="không dành cho server"):
        manager.content_versions(server.server_id, "modrinth", "mod", "voice")
    paper = manager.install("Paper", "paper", "1.21.1", "132")
    manager.content_versions(paper.server_id, "modrinth", "plugin", "chunky")
    query_url = http_client.requests[-1]
    rows = as_list(http_client.document(query_url))
    fields = as_mapping(rows[0])
    for game_versions, loaders in ((["1.20.1"], ["paper"]), (["1.21.1"], ["fabric"])):
        http_client.overrides[query_url] = [
            fields | {"game_versions": game_versions, "loaders": loaders}
        ]
        with pytest.raises(ServerError):
            manager.install_content(paper.server_id, "modrinth", "plugin", "chunky", "chunky-v1")
    assert manager.installed_content(paper.server_id) == ()


def test_required_dependency_install_is_idempotent_and_corrupt_batch_rolls_back(
    tmp_path: Path,
) -> None:
    launcher, http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Paper", "paper", "1.21.1", "132")
    manager.content_versions(server.server_id, "modrinth", "plugin", "luckperms")
    query_url = http_client.requests[-1]
    fields = as_mapping(as_list(http_client.document(query_url))[0])
    http_client.overrides[query_url] = [
        fields | {"dependencies": [{"project_id": "voice", "dependency_type": "required"}]}
    ]
    http_client.corrupt = True
    with pytest.raises(IntegrityError):
        manager.install_content(server.server_id, "modrinth", "plugin", "luckperms", "luckperms-v1")
    assert manager.installed_content(server.server_id) == ()
    http_client.corrupt = False
    manager.install_content(server.server_id, "modrinth", "plugin", "luckperms", "luckperms-v1")
    assert {row.file_name for row in manager.installed_content(server.server_id)} == {
        "voice.jar",
        "luckperms.jar",
    }
    manager.install_content(server.server_id, "modrinth", "plugin", "luckperms", "luckperms-v1")
    assert len(manager.installed_content(server.server_id)) == 2
    directory = manager.directory(server.server_id)
    (directory / "plugins" / "chunky.jar").write_bytes(jar_bytes())
    with pytest.raises(ServerError, match="ghi đè"):
        manager.install_content(server.server_id, "modrinth", "plugin", "chunky", "chunky-v1")
    assert any(row.source == "manual" for row in manager.installed_content(server.server_id))
    manager.remove_content(server.server_id, "plugin", "luckperms.jar")
    assert (directory / ".nostalgia" / "removed" / "luckperms.jar").is_file()
    assert not (directory / "plugins" / "luckperms.jar").exists()


def test_modrinth_v2_plugin_classified_as_mod_still_requires_plugin_loader(tmp_path: Path) -> None:
    launcher, http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Paper", "paper", "1.21.1", "132")
    url = "https://api.modrinth.com/v2/project/luckperms"
    http_client.overrides[url] = {
        "project_type": "mod",
        "server_side": "required",
        "loaders": ["bukkit", "paper", "fabric"],
    }
    assert manager.content_versions(server.server_id, "modrinth", "plugin", "luckperms")
    http_client.overrides[url] = {
        "project_type": "mod",
        "server_side": "required",
        "loaders": ["fabric"],
    }
    with pytest.raises(ServerError):
        manager.content_versions(server.server_id, "modrinth", "plugin", "luckperms")


def test_hangar_release_filters_external_and_required_manual_dependencies(tmp_path: Path) -> None:
    launcher, http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    server = manager.install("Paper", "paper", "1.21.1", "132")
    url = "https://hangar.papermc.io/api/v1/projects/Owner/Plugin/versions?limit=100&platform=PAPER&channel=Release"
    document = {
        "name": "1.0",
        "channel": {"name": "Release"},
        "platformDependencies": {"PAPER": ["1.21.1"]},
        "downloads": {
            "PAPER": {
                "downloadUrl": "https://hangarcdn.papermc.io/plugin.jar",
                "externalUrl": None,
                "fileInfo": {"sha256Hash": "a" * 64, "name": "plugin.jar", "sizeBytes": 100},
            }
        },
    }
    http_client.overrides[url] = {
        "result": [
            document,
            document | {"channel": {"name": "Snapshot"}},
            document | {"platformDependencies": {"PAPER": ["1.20.1"]}},
            document | {"pluginDependencies": {"PAPER": [{"required": True}]}},
            document | {"downloads": {"PAPER": {"externalUrl": "https://example.com"}}},
        ]
    }
    versions = manager.content_versions(server.server_id, "hangar", "plugin", "Owner/Plugin")
    assert len(versions) == 1 and versions[0].version_id == "1.0"
    assert http_client.requests[-1] == url
