"""Cài modpack Modrinth thành bản chơi mới, trọn vòng qua máy chủ giả: tải .mrpack -> cài
Fabric đúng bản pack đòi -> đăng ký bản chơi -> tải mod -> chép overrides -> dọn file tạm."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

import pytest

from fabric_fixture import LOADER_VERSION, publish_fabric
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Launcher
from nostalgia.content.model import Project
from nostalgia.errors import ContentError
from test_api import make_launcher

PACK_ID = "goivui"
MOD_BODY = b"noi dung mod" * 9


def modpack_project() -> Project:
    return Project(
        project_id=PACK_ID,
        project_slug="goi-vui",
        title="Gói Vui",
        description="",
        author="",
        content_kind="modpack",
        icon_url="",
        downloads=0,
        follows=0,
        loaders=("fabric",),
    )


def publish_modpack(server: LocalHttpsServer, state: ServerState) -> str:
    """Trả về host của máy chủ giả để test cho phép tải từ đó."""
    mod_url = server.url(state.add("/files/sodium.jar", MOD_BODY))
    index = {
        "formatVersion": 1,
        "name": "Gói Vui",
        "dependencies": {"minecraft": VERSION_ID, "fabric-loader": LOADER_VERSION},
        "files": [
            {
                "path": "mods/sodium.jar",
                "downloads": [mod_url],
                "hashes": {"sha1": hashlib.sha1(MOD_BODY).hexdigest()},
                "fileSize": len(MOD_BODY),
            }
        ],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("modrinth.index.json", json.dumps(index))
        archive.writestr("overrides/config/goi.toml", b"cau hinh")
    mrpack = buffer.getvalue()
    mrpack_url = server.url(state.add("/files/goi-vui.mrpack", mrpack))
    state.add(
        f"/modrinth/project/{PACK_ID}/version",
        json.dumps(
            [
                {
                    "id": "v1",
                    "project_id": PACK_ID,
                    "version_number": "1.0",
                    "version_type": "release",
                    "game_versions": [VERSION_ID],
                    "loaders": ["fabric"],
                    "date_published": "2026-01-01",
                    "files": [
                        {
                            "url": mrpack_url,
                            "filename": "goi-vui.mrpack",
                            "primary": True,
                            "size": len(mrpack),
                            "hashes": {"sha1": hashlib.sha1(mrpack).hexdigest()},
                        }
                    ],
                    "dependencies": [],
                }
            ]
        ).encode(),
    )
    return urlparse(mod_url).hostname or ""


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
