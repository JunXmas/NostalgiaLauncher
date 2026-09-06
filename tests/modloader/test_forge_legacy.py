"""Forge đời cũ (<=1.12.1): cài từ install_profile.json của installer, không chạy Java."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from test_forge import make_forge_launcher

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.repo.version_repo import VersionRepository


def legacy_installer_jar(maven_url: str) -> bytes:
    """Installer Forge cũ giả: install_profile có versionInfo, kèm jar universal. Mọi thư viện
    trỏ `url` về máy chủ giả — không có url thì parser mặc định libraries.minecraft.net thật."""
    version_info = {
        "id": f"{VERSION_ID}-Forge10.13.4.1614-{VERSION_ID}",
        "inheritsFrom": VERSION_ID,
        "jar": VERSION_ID,
        "mainClass": "net.minecraft.launchwrapper.Launch",
        "minecraftArguments": "--username ${auth_player_name} --tweakClass cpw.mods.fml.FMLTweaker",
        "libraries": [
            {
                "name": f"net.minecraftforge:forge:{VERSION_ID}-10.13.4.1614-{VERSION_ID}",
                "url": maven_url,
            },
            {"name": "net.minecraft:launchwrapper:1.12", "url": maven_url, "serverreq": True},
            {"name": "chi.server:thu:1.0", "clientreq": False, "serverreq": True},
        ],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "install_profile.json",
            json.dumps(
                {
                    "install": {
                        "path": f"net.minecraftforge:forge:{VERSION_ID}-10.13.4.1614-{VERSION_ID}",
                        "filePath": "forge-universal.jar",
                    },
                    "versionInfo": version_info,
                }
            ),
        )
        archive.writestr("forge-universal.jar", b"noi dung universal")
    return buffer.getvalue()


def test_legacy_forge_is_installed_from_the_profile_without_running_java(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Installer <=1.12.1: version JSON lấy từ versionInfo (bỏ lib server-only), jar universal
    vào libraries/ theo toạ độ maven, "java" giả KHÔNG được gọi."""
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)
    legacy_name = f"{VERSION_ID}-10.13.4.1614-{VERSION_ID}"
    server_state.add(
        "/forge/maven-metadata.xml",
        f"<metadata><versioning><versions><version>{legacy_name}</version>"
        f"</versions></versioning></metadata>".encode(),
    )
    server_state.add(
        f"/forge/{legacy_name}/forge-{legacy_name}-installer.jar",
        legacy_installer_jar(server.url("/maven/")),
    )
    server_state.add("/maven/net/minecraft/launchwrapper/1.12/launchwrapper-1.12.jar", b"lw")

    report = launcher.install_loader("forge", VERSION_ID, legacy_name)

    version_id = f"{VERSION_ID}-Forge10.13.4.1614-{VERSION_ID}"
    assert report.version_meta.version_id == version_id
    merged = VersionRepository(launcher.paths).load_version_meta(version_id)
    assert merged.main_class == "net.minecraft.launchwrapper.Launch"
    names = {str(library.coordinate) for library in merged.libraries}
    assert "chi.server:thu:1.0" not in names, "thư viện chỉ cho server bị bỏ"
    assert "net.minecraft:launchwrapper:1.12" in names
    universal = (
        launcher.paths.libraries_dir
        / "net/minecraftforge/forge"
        / legacy_name
        / f"forge-{legacy_name}.jar"
    )
    assert universal.read_bytes() == b"noi dung universal"
    assert not (launcher.paths.data_dir / "launcher_profiles.json").exists(), "không chạy Java"
    assert list((launcher.paths.data_dir / "installers").iterdir()) == []


def test_old_forge_names_are_sorted_by_build_and_recommended_matches_the_suffix() -> None:
    """Lỗi thật: maven-metadata xếp 1.7.10 lẫn lộn nên "mới nhất" ra build 1150 (launchwrapper 1.9
    chết vì ConcurrentModificationException), và recommended không được đánh dấu vì tên
    mang hậu tố `-1.7.10`."""
    from nostalgia.modloader.forge import forge_build_number

    assert forge_build_number("1.7.10-10.13.4.1614-1.7.10", "1.7.10-") == (10, 13, 4, 1614)
    assert forge_build_number("1.20.1-47.4.10", "1.20.1-") == (47, 4, 10)
    assert forge_build_number("1.7.10-10.13.0.1150", "1.7.10-") < forge_build_number(
        "1.7.10-10.13.4.1614-1.7.10", "1.7.10-"
    )


def test_recommended_old_forge_wins_even_when_the_list_is_shuffled(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    import json as json_module

    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)
    names = [
        f"{VERSION_ID}-10.13.4.1614-{VERSION_ID}",
        f"{VERSION_ID}-10.13.0.1150",
        f"{VERSION_ID}-10.13.2.1291",
    ]
    server_state.add(
        "/forge/maven-metadata.xml",
        (
            "<metadata><versioning><versions>"
            + "".join(f"<version>{name}</version>" for name in names)
            + "</versions></versioning></metadata>"
        ).encode(),
    )
    server_state.add(
        "/forge-promos.json",
        json_module.dumps({"promos": {f"{VERSION_ID}-recommended": "10.13.4.1614"}}).encode(),
    )

    versions = launcher.list_loader_versions("forge", VERSION_ID)

    assert [v.loader_version for v in versions] == [
        f"{VERSION_ID}-10.13.4.1614-{VERSION_ID}",
        f"{VERSION_ID}-10.13.2.1291",
        f"{VERSION_ID}-10.13.0.1150",
    ]
    assert [v.stable for v in versions] == [True, False, False]
