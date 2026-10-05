"""Modpack Modrinth giả: một .mrpack Fabric cho bản giả 1.99.9 với một mod và một override."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from urllib.parse import urlparse

from fabric_fixture import LOADER_VERSION
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.content.model import Project

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
