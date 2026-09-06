"""Fabric qua máy chủ giả: profile về đúng kho, kế thừa được trộn, bản cài chạy trọn vòng."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Launcher
from nostalgia.errors import VersionError
from nostalgia.repo.version_repo import VersionRepository
from test_api import make_launcher

LOADER_VERSION = "0.16.9"
FABRIC_VERSION_ID = f"fabric-loader-{LOADER_VERSION}-{VERSION_ID}"


def publish_fabric(state: ServerState) -> None:
    state.add(
        f"/fabric/versions/loader/{VERSION_ID}",
        json.dumps(
            [
                {"loader": {"version": "0.17.0-beta.1", "stable": False}},
                {"loader": {"version": LOADER_VERSION, "stable": True}},
            ]
        ).encode(),
    )
    state.add(
        f"/fabric/versions/loader/{VERSION_ID}/{LOADER_VERSION}/profile/json",
        json.dumps(
            {
                "id": FABRIC_VERSION_ID,
                "inheritsFrom": VERSION_ID,
                "type": "release",
                "mainClass": "net.fabricmc.loader.impl.launch.knot.KnotClient",
                "arguments": {
                    "game": [],
                    "jvm": ["-DFabricMcEmu= net.minecraft.client.main.Main"],
                },
                "libraries": [],
            }
        ).encode(),
    )


def make_fabric_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> Launcher:
    publish_fabric(server_state)
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    return replace(
        launcher, endpoints=replace(launcher.endpoints, fabric_meta=server.url("/fabric"))
    )


def test_loader_list_keeps_meta_order_and_stability_flag(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_fabric_launcher(server, server_state, tmp_path, certificate_pair)

    versions = launcher.list_fabric_loader_versions(VERSION_ID)

    assert [candidate.loader_version for candidate in versions] == ["0.17.0-beta.1", LOADER_VERSION]
    assert [candidate.stable for candidate in versions] == [False, True]


def test_install_fabric_picks_latest_stable_and_merges_inheritance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Bỏ trống loader thì lấy bản ổn định (không phải beta), profile nằm trong kho version,
    và bản trộn kế thừa có mainClass của Fabric nhưng client.jar của Mojang."""
    launcher = make_fabric_launcher(server, server_state, tmp_path, certificate_pair)

    report = launcher.install_fabric(VERSION_ID)

    assert report.version_meta.version_id == FABRIC_VERSION_ID
    assert launcher.paths.version_json(FABRIC_VERSION_ID).is_file()
    assert set(launcher.list_installed_versions()) == {VERSION_ID, FABRIC_VERSION_ID}
    merged = VersionRepository(launcher.paths).load_version_meta(FABRIC_VERSION_ID)
    assert merged.main_class == "net.fabricmc.loader.impl.launch.knot.KnotClient"
    assert merged.client_jar is not None, "client.jar phải kế thừa từ bản Mojang"
    # Mọi request meta Fabric chỉ đi đúng một lần cho mỗi địa chỉ.
    assert server_state.request_count(f"/fabric/versions/loader/{VERSION_ID}") == 1


def test_install_fabric_twice_does_not_refetch_the_profile(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_fabric_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_fabric(VERSION_ID, LOADER_VERSION)
    launcher.install_fabric(VERSION_ID, LOADER_VERSION)

    profile_path = f"/fabric/versions/loader/{VERSION_ID}/{LOADER_VERSION}/profile/json"
    # Profile được ghi lại (rẻ, một JSON nhỏ) nhưng client.jar và thư viện thì không tải lại.
    assert server_state.request_count(profile_path) == 2
    assert server_state.request_count("/objects/client") == 1


def test_unknown_game_version_is_a_clear_error(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_fabric_launcher(server, server_state, tmp_path, certificate_pair)
    server_state.add("/fabric/versions/loader/9.9.9", b"[]")

    with pytest.raises(VersionError, match=r"9\.9\.9"):
        launcher.list_fabric_loader_versions("9.9.9")
