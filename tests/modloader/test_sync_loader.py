"""Nhận đúng loader của profile thật; không nhầm thư viện hỗ trợ hoặc tên mod."""

from pathlib import Path

import pytest

from export_fixture import prepared_export
from nostalgia.api import Instance
from nostalgia.content import mrpack
from nostalgia.errors import MultiplayerError
from nostalgia.facade.sync_loader import resolve_sync_loader
from nostalgia.modloader.model import LoaderKind
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import atomic_write_json, read_json
from nostalgia.version.maven import MavenCoordinate
from nostalgia.version.meta import ArgumentSpec, Library
from nostalgia.version.rules import Rule


@pytest.mark.parametrize(
    "loader_kind,game_version,coordinate_text,expected",
    [
        ("fabric", "1.20.1", "net.fabricmc:fabric-loader:0.16.9", "0.16.9"),
        ("quilt", "1.20.1", "org.quiltmc:quilt-loader:0.26.0", "0.26.0"),
        ("forge", "1.20.1", "net.minecraftforge:fmlloader:1.20.1-47.4.23", "47.4.23"),
        ("forge", "1.21.1", "net.minecraftforge:fmlloader:1.21.1-52.1.1", "52.1.1"),
        ("forge", "1.20.1", "net.minecraftforge:forge:1.20.1-47.4.23:universal", "47.4.23"),
        (
            "forge",
            "1.7.10",
            "net.minecraftforge:forge:1.7.10-10.13.4.1614-1.7.10",
            "10.13.4.1614-1.7.10",
        ),
        ("neoforge", "1.21.1", "net.neoforged:neoforge:21.1.9", "21.1.9"),
        ("neoforge", "1.20.1", "net.neoforged:forge:1.20.1-47.1.79", "47.1.79"),
    ],
)
def test_resolves_installed_loader_coordinates(
    loader_kind: LoaderKind, game_version: str, coordinate_text: str, expected: str
) -> None:
    libraries = (Library(MavenCoordinate.parse(coordinate_text)),)
    assert resolve_sync_loader(loader_kind, libraries, game_version) == expected


@pytest.mark.parametrize(
    "loader_kind,coordinate_text",
    [
        ("forge", "example.mod:forge:99.9.9"),
        ("forge", "net.neoforged:fmlloader:4.0.42"),
        ("neoforge", "net.neoforged:fmlloader:4.0.42"),
        ("fabric", "example.mod:fabric-loader:99.9.9"),
    ],
)
def test_does_not_guess_loader_from_a_mod_or_an_independent_fml_release(
    loader_kind: LoaderKind, coordinate_text: str
) -> None:
    libraries = (Library(MavenCoordinate.parse(coordinate_text)),)
    with pytest.raises(MultiplayerError, match="phiên bản loader"):
        resolve_sync_loader(loader_kind, libraries, "1.20.1")


def test_vanilla_needs_no_loader_and_neoforge_prefers_primary_coordinate() -> None:
    assert resolve_sync_loader("vanilla", (), "1.20.1") == ""
    libraries = tuple(
        Library(MavenCoordinate.parse(coordinate_text))
        for coordinate_text in (
            "net.neoforged:fmlloader:4.0.42",
            "net.neoforged:forge:1.21.1-47.1.79",
            "net.neoforged:neoforge:21.1.9",
        )
    )
    assert resolve_sync_loader("neoforge", libraries, "1.21.1") == "21.1.9"


def test_official_forge_profile_shares_exports_and_scans_without_reinstall(tmp_path: Path) -> None:
    # version.json nguyên bản từ Forge 1.20.1-47.4.23-installer.jar, maven.minecraftforge.net.
    launcher = prepared_export(tmp_path, "forge")
    atomic_write_json(
        launcher.paths.version_json("1.20.1-forge-47.4.23"),
        read_json(Path(__file__).parent / "fixtures/forge-47.4.23-version.json"),
    )
    snapshot = launcher.capture_room_modpack(
        "custom", tmp_path / "snapshot", cancel_token=CancelToken()
    )
    assert (
        snapshot.manifest.game_version,
        snapshot.manifest.loader_kind,
        snapshot.manifest.loader_version,
    ) == ("1.20.1", "forge", "47.4.23")
    assert (snapshot.folder / "mods/local.jar").read_bytes() == b"custom mod"
    exported = launcher.export_instance_modpack("custom", tmp_path / "pack.mrpack", "mrpack")
    assert mrpack.read_index(exported.path).loader_version == "47.4.23"
    scan = launcher.scan_instance_mods("custom")
    assert (scan.game_version, scan.loader_kind, scan.loader_version) == (
        "1.20.1",
        "forge",
        "47.4.23",
    )
    assert len(launcher.list_instances()) == 1


@pytest.mark.parametrize(
    "game_version,loader_version",
    [("1.21.1", "21.1.200"), ("1.21.11", "21.11.0-beta"), ("26.2", "26.2.0.89")],
)
def test_official_neoforge_profile_shares_exports_and_scans_without_reinstall(
    tmp_path: Path, game_version: str, loader_version: str
) -> None:
    # version.json nguyên bản từ neoforge-{loader_version}-installer.jar tại
    # https://maven.neoforged.net/releases/net/neoforged/neoforge/{loader_version}/
    launcher = prepared_export(tmp_path, "neoforge")
    version_id = "neoforge-" + loader_version
    atomic_write_json(launcher.paths.version_json(game_version), {"id": game_version})
    atomic_write_json(
        launcher.paths.version_json(version_id),
        read_json(Path(__file__).parent / f"fixtures/neoforge-{loader_version}-version.json"),
    )
    launcher.save_instance(Instance("custom", version_id, "NeoForge"))
    snapshot = launcher.capture_room_modpack(
        "custom", tmp_path / "snapshot", cancel_token=CancelToken()
    )
    assert (
        snapshot.manifest.game_version,
        snapshot.manifest.loader_kind,
        snapshot.manifest.loader_version,
    ) == (game_version, "neoforge", loader_version)
    assert (snapshot.folder / "mods/local.jar").read_bytes() == b"custom mod"
    exported = launcher.export_instance_modpack("custom", tmp_path / "pack.mrpack", "mrpack")
    assert mrpack.read_index(exported.path).loader_version == loader_version
    scan = launcher.scan_instance_mods("custom")
    assert (scan.game_version, scan.loader_kind, scan.loader_version) == (
        game_version,
        "neoforge",
        loader_version,
    )
    assert len(launcher.list_instances()) == 1


@pytest.mark.parametrize(
    "values",
    [
        ("--fml.fmlVersion", "4.0.42"),
        ("--fml.neoForgeVersion",),
        ("--fml.neoForgeVersion", "--fml.mcVersion", "1.21.1"),
        ("--fml.neoForgeVersion", "${neoForgeVersion}"),
        ("--fml.neoForgeVersion", "../../21.1.200"),
        ("--fml.neoForgeVersion", "21.1.200", "--fml.neoForgeVersion", "21.1.201"),
    ],
)
def test_neoforge_arguments_do_not_guess_fml_or_invalid_versions(values: tuple[str, ...]) -> None:
    with pytest.raises(MultiplayerError, match="phiên bản loader"):
        resolve_sync_loader("neoforge", (), "1.21.1", game_arguments=(ArgumentSpec(values),))


def test_neoforge_arguments_are_not_used_for_other_loaders_or_conditional_profiles() -> None:
    arguments = (ArgumentSpec(("--fml.neoForgeVersion", "21.1.200")),)
    with pytest.raises(MultiplayerError, match="phiên bản loader"):
        resolve_sync_loader("forge", (), "1.21.1", game_arguments=arguments)
    with pytest.raises(MultiplayerError, match="phiên bản loader"):
        resolve_sync_loader(
            "neoforge",
            (),
            "1.21.1",
            game_arguments=(ArgumentSpec(arguments[0].values, (Rule("allow", os_name="osx"),)),),
        )
