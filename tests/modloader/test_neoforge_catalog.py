"""Danh mục NeoForge theo lịch năm chọn đúng nhánh, không lẫn các patch game."""

from pathlib import Path

import pytest
from test_forge import make_forge_launcher

from local_https_server import LocalHttpsServer, ServerState


@pytest.mark.parametrize(
    "game_version,loader_version", [("26.2", "26.2.0.89"), ("26.1.2", "26.1.2.115")]
)
def test_neoforge_calendar_catalog_filters_by_exact_game_branch(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    game_version: str,
    loader_version: str,
) -> None:
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)
    server_state.add(
        "/neoforge/maven-metadata.xml",
        (
            "<metadata><versioning><versions>"
            + "".join(
                f"<version>{name}</version>"
                for name in (
                    "20.4.80-beta",
                    "26.1.1.1",
                    "26.2.1.1",
                    "26.20.0.1",
                    loader_version + "-beta",
                    loader_version,
                )
            )
            + "</versions></versioning></metadata>"
        ).encode(),
    )
    versions = launcher.list_loader_versions("neoforge", game_version)
    assert [(candidate.loader_version, candidate.stable) for candidate in versions] == [
        (loader_version, True),
        (loader_version + "-beta", False),
    ]
    assert versions[0].installer_url.endswith(
        f"/{loader_version}/neoforge-{loader_version}-installer.jar"
    )
