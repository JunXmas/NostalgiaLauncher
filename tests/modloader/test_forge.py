"""Forge/NeoForge qua máy chủ giả và một "java" giả: danh sách bản, chạy installer, kế thừa."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Launcher
from nostalgia.errors import VersionError
from nostalgia.modloader.forge import neoforge_prefix
from nostalgia.repo.version_repo import VersionRepository
from test_api import make_launcher

FORGE_NAME = f"{VERSION_ID}-47.2.0"
FORGE_VERSION_ID = f"{VERSION_ID}-forge-47.2.0"
NEOFORGE_NAME = "99.9.1"
FAKE_JAVA = f"""#!/bin/sh
# "java" giả: đóng vai installer --installClient, ghi version JSON kế thừa bản gốc.
data_dir="$4"
case "$2" in
  *neoforge*) id="neoforge-{NEOFORGE_NAME}" ;;
  *) id="{FORGE_VERSION_ID}" ;;
esac
test -f "$data_dir/launcher_profiles.json" || exit 3
mkdir -p "$data_dir/versions/$id"
main_class="cpw.mods.bootstraplauncher.BootstrapLauncher"
printf '{{"id":"%s","inheritsFrom":"{VERSION_ID}","mainClass":"%s","libraries":[]}}' \\
  "$id" "$main_class" > "$data_dir/versions/$id/$id.json"
echo "Successfully installed client into launcher."
"""


def installer_jar(*, legacy: bool = False) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        install_profile: dict[str, object] = {"processors": []}
        if legacy:
            install_profile = {"versionInfo": {"id": "old"}, "install": {}}
        archive.writestr("install_profile.json", json.dumps(install_profile))
    return buffer.getvalue()


def publish_forge(state: ServerState, *, legacy: bool = False) -> None:
    state.add(
        "/forge/maven-metadata.xml",
        f"<metadata><versioning><versions><version>1.7.10-10.13.4.1614-1.7.10</version>"
        f"<version>{VERSION_ID}-47.1.0</version><version>{FORGE_NAME}</version>"
        f"</versions></versioning></metadata>".encode(),
    )
    state.add(
        "/forge-promos.json",
        json.dumps(
            {"promos": {f"{VERSION_ID}-recommended": "47.1.0", f"{VERSION_ID}-latest": "47.2.0"}}
        ).encode(),
    )
    state.add(f"/forge/{FORGE_NAME}/forge-{FORGE_NAME}-installer.jar", installer_jar(legacy=legacy))
    state.add(
        "/neoforge/maven-metadata.xml",
        f"<metadata><versioning><versions><version>20.4.80-beta</version>"
        f"<version>{NEOFORGE_NAME}-beta</version><version>{NEOFORGE_NAME}</version>"
        f"</versions></versioning></metadata>".encode(),
    )
    state.add(f"/neoforge/{NEOFORGE_NAME}/neoforge-{NEOFORGE_NAME}-installer.jar", installer_jar())


def make_forge_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    *,
    legacy: bool = False,
) -> Launcher:
    publish_forge(server_state, legacy=legacy)
    launcher = make_launcher(
        server, server_state, tmp_path, certificate_pair, java_body=FAKE_JAVA.encode()
    )
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            forge_maven=server.url("/forge"),
            forge_promotions=server.url("/forge-promos.json"),
            neoforge_maven=server.url("/neoforge"),
        ),
    )
    return launcher


def test_forge_versions_newest_first_with_recommended_flag(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)

    versions = launcher.list_loader_versions("forge", VERSION_ID)

    assert [(v.loader_version, v.stable) for v in versions] == [
        (FORGE_NAME, False),
        (f"{VERSION_ID}-47.1.0", True),
    ]
    assert versions[0].installer_url.endswith(
        f"/forge/{FORGE_NAME}/forge-{FORGE_NAME}-installer.jar"
    )


def test_neoforge_versions_filter_by_game_and_flag_betas(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)

    versions = launcher.list_loader_versions("neoforge", "1.99.9")

    assert [(v.loader_version, v.stable) for v in versions] == [
        (NEOFORGE_NAME, True),
        (f"{NEOFORGE_NAME}-beta", False),
    ]
    assert neoforge_prefix("1.21") == "21.0."
    assert neoforge_prefix("1.20.4") == "20.4."


def test_install_forge_runs_installer_and_merges_inheritance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)

    report = launcher.install_loader("forge", VERSION_ID, FORGE_NAME)

    assert report.version_meta.version_id == FORGE_VERSION_ID
    merged = VersionRepository(launcher.paths).load_version_meta(FORGE_VERSION_ID)
    assert merged.main_class == "cpw.mods.bootstraplauncher.BootstrapLauncher"
    assert merged.client_jar is not None
    # Installer jar không nằm lại trên đĩa; launcher_profiles.json thì có (installer đòi).
    assert list((launcher.paths.data_dir / "installers").iterdir()) == []
    assert (launcher.paths.data_dir / "launcher_profiles.json").is_file()


def test_install_neoforge_picks_stable_when_unspecified(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)

    report = launcher.install_loader("neoforge", VERSION_ID)

    assert report.version_meta.version_id == f"neoforge-{NEOFORGE_NAME}"


def test_unknown_loader_version_is_a_clear_error(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)

    with pytest.raises(VersionError, match="không có bản loader"):
        launcher.install_loader("forge", VERSION_ID, "1.99.9-0.0.0")
