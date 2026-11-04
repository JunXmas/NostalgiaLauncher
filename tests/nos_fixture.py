"""Jar Fabric tối thiểu có ZIP/metadata thật cho kiểm thử cập nhật Nos Client."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile

from nostalgia.model.json_value import JsonValue


def build_nos_jar(
    game_version: str = "1.21.11",
    *,
    mod_id: str = "nosclient",
    mod_version: str = "0.4.2",
    loader_version: str = ">=0.19.3",
    java_requirement: str = ">=21",
) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as jar:
        jar.writestr(
            zipfile.ZipInfo("fabric.mod.json", date_time=(2020, 1, 1, 0, 0, 0)),
            json.dumps(
                {
                    "schemaVersion": 1,
                    "id": mod_id,
                    "version": mod_version,
                    "depends": {
                        "minecraft": game_version,
                        "fabricloader": loader_version,
                        "java": java_requirement,
                    },
                }
            ),
        )
        jar.writestr(zipfile.ZipInfo("content.txt", date_time=(2020, 1, 1, 0, 0, 0)), "Nos Client")
    return stream.getvalue()


def build_nos_release(file_name: str, url: str, body: bytes) -> dict[str, JsonValue]:
    return {
        "tag_name": "v" + file_name.removeprefix("nos-client-").removesuffix(".jar"),
        "draft": False,
        "prerelease": False,
        "assets": [
            {
                "name": file_name,
                "browser_download_url": url,
                "size": len(body),
                "digest": "sha256:" + hashlib.sha256(body).hexdigest(),
            }
        ],
    }
