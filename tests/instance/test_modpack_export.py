"""Gói xuất đọc được bằng hai định dạng chuẩn, giữ loader và dữ liệu tùy chọn."""

from dataclasses import replace
from pathlib import Path

import pytest

from export_fixture import prepared_export
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance
from nostalgia.content import cfpack, mrpack
from nostalgia.modloader.model import LoaderKind
from test_api import make_launcher


@pytest.mark.parametrize("archive_format", ["mrpack", "zip"])
@pytest.mark.parametrize("include_worlds", [False, True])
@pytest.mark.parametrize("loader_kind", ["vanilla", "fabric", "quilt", "forge", "neoforge"])
def test_export_import_preserves_loader_payload_and_optional_worlds(
    tmp_path: Path,
    archive_format: str,
    include_worlds: bool,
    loader_kind: LoaderKind,
) -> None:
    launcher = prepared_export(tmp_path, loader_kind)
    destination = tmp_path / ("shared." + archive_format)
    exported = launcher.export_instance_modpack(
        "custom",
        destination,
        archive_format,
        include_worlds=include_worlds,
    )
    imported = tmp_path / "imported"
    description: mrpack.ModpackIndex | cfpack.PackManifest
    if archive_format == "mrpack":
        description = mrpack.read_index(destination)
        mrpack.apply_overrides(destination, imported)
    else:
        description = cfpack.read_manifest(destination)
        cfpack.apply_overrides(destination, imported, description.overrides_prefix)
    assert (description.name, description.game_version, description.loader_kind) == (
        "Gói của tôi",
        "1.20.1",
        loader_kind,
    )
    assert (
        description.loader_version
        == {
            "vanilla": "",
            "fabric": "0.16.9",
            "quilt": "0.26.0",
            "forge": "47.4.23",
            "neoforge": "21.1.9",
        }[loader_kind]
    )
    original = launcher.paths.instance_dir("custom")
    for relative_path in (
        "mods/local.jar",
        "mods/optional.jar.disabled",
        "resourcepacks/textures.zip",
        "shaderpacks/shader.zip",
        "config/client.toml",
        "kubejs/server_scripts/custom.js",
    ):
        assert (imported / relative_path).read_bytes() == (original / relative_path).read_bytes()
    assert (imported / "saves/My world/level.dat").exists() == include_worlds
    assert not (imported / "logs").exists() and not (imported / "accounts.json").exists()
    assert not (imported / "mods/.nostalgia-content.json").exists()
    assert (original / "saves/My world/level.dat").read_bytes() == b"world"
    assert exported.file_count == 6 + include_worlds and exported.size_bytes > 0


@pytest.mark.parametrize("archive_format", ["mrpack", "zip"])
def test_exported_archive_imports_through_the_real_launcher(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    certificate_pair: tuple[Path, Path],
    archive_format: str,
) -> None:
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            modrinth_api=server.url("/modrinth"),
        ),
    )
    server_state.add("/modrinth/version_files", b"{}")
    launcher.install_version(VERSION_ID)
    launcher.save_instance(Instance("original", VERSION_ID, "Custom pack"))
    source = launcher.paths.instance_dir("original") / "mods/local.jar"
    source.parent.mkdir()
    source.write_bytes(b"custom content")
    archive = tmp_path / ("share." + archive_format)
    launcher.export_instance_modpack("original", archive, archive_format)
    restored = launcher.install_modpack_file(archive, "imported")
    assert restored.version_id == VERSION_ID and restored.label == "Custom pack"
    assert (
        launcher.instance_game_dir(restored) / "mods/local.jar"
    ).read_bytes() == source.read_bytes()
