"""Modpack Forge/NeoForge: phiên bản ngắn trong manifest, bản chơi dùng đúng loader vừa cài."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest
from test_forge import FORGE_VERSION_ID, NEOFORGE_NAME, make_forge_launcher

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modpack_fixture import MOD_BODY, PACK_ID, modpack_project, publish_modpack
from nostalgia.modloader.model import LoaderKind
from nostalgia.storage.files import atomic_write_json


@pytest.mark.parametrize("source", ["modrinth", "curseforge"])
@pytest.mark.parametrize("loader_kind", ["forge", "neoforge"])
@pytest.mark.parametrize("already_installed", [False, True])
def test_modpack_uses_the_installed_loader(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    source: str,
    loader_kind: LoaderKind,
    already_installed: bool,
) -> None:
    launcher = make_forge_launcher(server, server_state, tmp_path, certificate_pair)
    host = publish_modpack(server, server_state)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, modrinth_api=server.url("/modrinth"))
    )
    loader_version = "47.2.0" if loader_kind == "forge" else NEOFORGE_NAME
    expected_id = FORGE_VERSION_ID if loader_kind == "forge" else f"neoforge-{NEOFORGE_NAME}"
    # Một bản khác đã có sẵn không được làm pack dùng nhầm loader.
    if already_installed:
        other_id = f"{loader_kind}-999-{VERSION_ID}"
        atomic_write_json(launcher.paths.version_json(other_id), {"id": other_id})
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        if source == "modrinth":
            archive.writestr(
                "modrinth.index.json",
                json.dumps(
                    {
                        "formatVersion": 1,
                        "name": "Gói Forge",
                        "dependencies": {"minecraft": VERSION_ID, loader_kind: loader_version},
                        "files": [
                            {
                                "path": "mods/sodium.jar",
                                "downloads": [server.url("/files/sodium.jar")],
                                "hashes": {"sha1": hashlib.sha1(MOD_BODY).hexdigest()},
                                "fileSize": len(MOD_BODY),
                            }
                        ],
                    }
                ),
            )
        else:
            archive.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "manifestType": "minecraftModpack",
                        "manifestVersion": 1,
                        "name": "Gói Forge",
                        "minecraft": {
                            "version": VERSION_ID,
                            "modLoaders": [
                                {"id": f"{loader_kind}-{loader_version}", "primary": True}
                            ],
                        },
                        "files": [],
                        "overrides": "overrides",
                    }
                ),
            )
        archive.writestr("overrides/config/goi.toml", b"cau hinh")
    pack_body = buffer.getvalue()
    if source == "modrinth":
        # Tạo bản chơi từ thư viện, đúng luồng trong ảnh báo lỗi.
        server_state.add("/files/goi-vui.mrpack", pack_body)
        server_state.add(
            f"/modrinth/project/{PACK_ID}/version",
            json.dumps(
                [
                    {
                        "id": "v1",
                        "project_id": PACK_ID,
                        "files": [
                            {
                                "url": server.url("/files/goi-vui.mrpack"),
                                "filename": "goi-vui.mrpack",
                                "primary": True,
                                "size": len(pack_body),
                                "hashes": {"sha1": hashlib.sha1(pack_body).hexdigest()},
                            }
                        ],
                    }
                ]
            ).encode(),
        )
        instance = launcher.install_modpack(modpack_project(), "forge-pack", allowed_hosts=(host,))
        assert (launcher.instance_game_dir(instance) / "mods/sodium.jar").read_bytes() == MOD_BODY
    else:
        pack_path = tmp_path / "forge-pack.zip"
        pack_path.write_bytes(pack_body)
        instance = launcher.install_modpack_file(pack_path, "forge-pack")
    assert instance.version_id == expected_id
    assert launcher.paths.version_json(expected_id).is_file()
    assert (launcher.instance_game_dir(instance) / "config/goi.toml").read_bytes() == b"cau hinh"
