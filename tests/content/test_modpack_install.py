"""Cài modpack Modrinth thành bản chơi mới, trọn vòng qua máy chủ giả: tải .mrpack -> cài
Fabric đúng bản pack đòi -> đăng ký bản chơi -> tải mod -> chép overrides -> dọn file tạm."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from fabric_fixture import LOADER_VERSION, publish_fabric
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modpack_fixture import MOD_BODY, PACK_ID, modpack_project, publish_modpack
from nostalgia.api import Launcher
from nostalgia.errors import ContentError
from test_api import make_launcher


def make_modpack_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> tuple[Launcher, str]:
    publish_fabric(server_state)
    host = publish_modpack(server, server_state)
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher = replace(
        launcher,
        endpoints=replace(
            launcher.endpoints,
            fabric_meta=server.url("/fabric"),
            modrinth_api=server.url("/modrinth"),
        ),
    )
    return launcher, host


def test_modpack_becomes_a_playable_instance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher, host = make_modpack_launcher(server, server_state, tmp_path, certificate_pair)

    instance = launcher.install_modpack(modpack_project(), "goi-vui", allowed_hosts=(host,))

    assert instance.display_name == "Gói Vui"
    assert instance.version_id == f"fabric-loader-{LOADER_VERSION}-{VERSION_ID}"
    game_dir = launcher.paths.instance_dir("goi-vui")
    assert (game_dir / "mods" / "sodium.jar").read_bytes() == MOD_BODY
    assert (game_dir / "config" / "goi.toml").read_bytes() == b"cau hinh"
    assert list((launcher.paths.data_dir / "installers").iterdir()) == []
    assert [i.instance_id for i in launcher.list_instances()] == ["goi-vui"]
    target = launcher.describe_content_target("goi-vui")
    assert (target.game_version, target.loader_kind) == (VERSION_ID, "fabric")


def test_modpack_refuses_unknown_hosts_by_default(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Không truyền allowed_hosts thì máy chủ giả (localhost) là host lạ: pack bị từ chối và
    KHÔNG có bản chơi nào được tạo dở."""
    launcher, _host = make_modpack_launcher(server, server_state, tmp_path, certificate_pair)

    with pytest.raises(ContentError, match="host không được phép"):
        launcher.install_modpack(modpack_project(), "goi-vui")
    assert launcher.list_instances() == ()


def test_duplicate_instance_id_is_refused_before_any_download(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    from nostalgia.api import Instance

    launcher, host = make_modpack_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.create_instance(Instance(instance_id="goi-vui", version_id=VERSION_ID))

    with pytest.raises(ContentError, match="đã có bản chơi"):
        launcher.install_modpack(modpack_project(), "goi-vui", allowed_hosts=(host,))
    assert server_state.request_count(f"/modrinth/project/{PACK_ID}/version") == 0


def test_pack_version_prefers_the_filtered_game_version() -> None:
    """Đang lọc 26.2 thì lấy bản pack cho 26.2 dù nó là beta; không lọc thì release mới nhất."""
    from nostalgia.content.model import ProjectVersion
    from nostalgia.facade.modpacks import choose_pack_version

    def make(version_id: str, version_type: str, games: tuple[str, ...]) -> ProjectVersion:
        return ProjectVersion(
            version_id=version_id,
            project_id="p",
            version_number=version_id,
            version_type=version_type,
            game_versions=games,
            loaders=("fabric",),
            date_published="",
            file_url="u",
            file_name="f.mrpack",
            file_sha1="0" * 40,
            file_size=1,
            required_project_ids=(),
        )

    beta_262 = make("b7", "beta", ("26.2",))
    release_2612 = make("r14", "release", ("26.1.2",))
    old_release_262 = make("r13", "release", ("26.2", "26.1.2"))
    newest_first = (beta_262, release_2612, old_release_262)

    assert choose_pack_version(newest_first, "26.2") is old_release_262, (
        "release cho 26.2 thắng beta"
    )
    assert choose_pack_version((beta_262, release_2612), "26.2") is beta_262, (
        "chỉ có beta cho 26.2 thì lấy nó"
    )
    assert choose_pack_version(newest_first, "") is release_2612, "không lọc: release mới nhất"
    assert choose_pack_version(newest_first, "1.20.1") is release_2612, (
        "không có bản khớp: rơi về release"
    )
