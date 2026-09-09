"""Một máy chủ Mojang giả đủ để cài trọn vẹn một phiên bản — không cần Internet.

Dựng đúng năm thứ mà một lượt cài thật phải đi qua: danh mục phiên bản, JSON phiên bản,
client.jar, thư viện (kèm một jar natives thật để bung), chỉ mục asset với một object, và
hai tầng manifest bản Java. Nhờ vậy `install_version` được kiểm từ đầu đến cuối mà vẫn chạy
trong một phần giây.

Nội dung file do chính đây sinh ra nên sha1 luôn khớp — điều kiện để đường xác minh được đi
qua thật chứ không bị bỏ trống.
"""

from __future__ import annotations

import hashlib
import io
import json
import lzma
import zipfile

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.java.unpack import LZMA_FORMAT
from nostalgia.repo.endpoints import Endpoints

VERSION_ID = "1.99.9"
JAVA_COMPONENT = "jre-legacy"
CLIENT_BODY = b"noi dung client jar" * 8
LIBRARY_BODY = b"noi dung thu vien" * 8
ASSET_BODY = b"noi dung mot asset" * 8
JAVA_BODY = b"#!/bin/sh\necho fake java\n"
NATIVE_MEMBER = b"noi dung file .so" * 8


def digest(payload: bytes) -> str:
    return hashlib.sha1(payload).hexdigest()


def remote(url: str, payload: bytes) -> dict[str, object]:
    return {"url": url, "sha1": digest(payload), "size": len(payload)}


def natives_jar() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("linux/x64/libthu.so", NATIVE_MEMBER)
        archive.writestr("META-INF/MANIFEST.MF", b"bi loai")
    return buffer.getvalue()


def publish(
    server: LocalHttpsServer, state: ServerState, *, java_body: bytes = JAVA_BODY
) -> Endpoints:
    """Đăng ký mọi tài nguyên lên máy chủ cục bộ và trả về các địa chỉ gốc.

    `java_body` cho test thay "java" bằng một script đóng vai khác (vd installer Forge).
    """
    natives_body = natives_jar()
    asset_hash = digest(ASSET_BODY)
    asset_index_document = {
        "objects": {"minecraft/am.ogg": {"hash": asset_hash, "size": len(ASSET_BODY)}}
    }
    asset_index_body = json.dumps(asset_index_document).encode()

    state.add("/objects/client", CLIENT_BODY)
    state.add("/objects/vien", LIBRARY_BODY)
    state.add("/objects/nat", natives_body)
    state.add("/objects/asset-index", asset_index_body)
    state.add(f"/assets/{asset_hash[:2]}/{asset_hash}", ASSET_BODY)

    version_document = {
        "id": VERSION_ID,
        "type": "release",
        "mainClass": "net.minecraft.client.main.Main",
        "assets": "kt",
        # Dùng định dạng tham số ĐỜI MỚI, kèm khối phụ thuộc cờ tính năng đúng như Mojang
        # khai ở 1.20.1 — nhờ vậy đường "chỉ thêm --width khi người dùng đặt kích thước" được
        # đi qua thật, chứ không chỉ được kiểm bằng fixture tĩnh.
        "arguments": {
            "game": [
                "--username",
                "${auth_player_name}",
                "--gameDir",
                "${game_directory}",
                {
                    "rules": [{"action": "allow", "features": {"has_custom_resolution": True}}],
                    "value": ["--width", "${resolution_width}", "--height", "${resolution_height}"],
                },
                # Khối quick play y như 1.20+: chỉ hiện khi façade được bảo vào thẳng một thế giới.
                {
                    "rules": [
                        {"action": "allow", "features": {"is_quick_play_singleplayer": True}}
                    ],
                    "value": ["--quickPlaySingleplayer", "${quickPlaySingleplayer}"],
                },
            ]
        },
        "javaVersion": {"component": JAVA_COMPONENT, "majorVersion": 8},
        "assetIndex": {"id": "kt", **remote(server.url("/objects/asset-index"), asset_index_body)},
        "downloads": {"client": remote(server.url("/objects/client"), CLIENT_BODY)},
        "libraries": [
            {
                "name": "org.thu:vien:1.0",
                "downloads": {
                    "artifact": {
                        "path": "org/thu/vien/1.0/vien-1.0.jar",
                        **remote(server.url("/objects/vien"), LIBRARY_BODY),
                    }
                },
            },
            {
                "name": "org.thu:nat:1.0",
                "natives": {"linux": "natives-linux", "windows": "natives-windows"},
                "downloads": {
                    "classifiers": {
                        "natives-linux": {
                            "path": "org/thu/nat/1.0/nat-1.0-natives-linux.jar",
                            **remote(server.url("/objects/nat"), natives_body),
                        }
                    }
                },
            },
        ],
    }
    version_body = json.dumps(version_document).encode()
    state.add("/versions/1.99.9.json", version_body)
    manifest_url = state.add(
        "/manifest.json",
        json.dumps(
            {
                "latest": {"release": VERSION_ID, "snapshot": VERSION_ID},
                "versions": [
                    {
                        "id": VERSION_ID,
                        "type": "release",
                        **remote(server.url("/versions/1.99.9.json"), version_body),
                    }
                ],
            }
        ).encode(),
    )

    return Endpoints(
        version_manifest=server.url(manifest_url),
        java_catalog=server.url(_publish_java(server, state, java_body)),
        asset_objects=server.url("/assets"),
    )


def _publish_java(server: LocalHttpsServer, state: ServerState, java_body: bytes) -> str:
    compressed = lzma.compress(java_body, format=LZMA_FORMAT)
    state.add("/java/bin-java.lzma", compressed)
    runtime_document = {
        "files": {
            "bin": {"type": "directory"},
            "bin/java": {
                "type": "file",
                "executable": True,
                "downloads": {
                    "raw": remote(server.url("/java/bin-java"), java_body),
                    "lzma": remote(server.url("/java/bin-java.lzma"), compressed),
                },
            },
        }
    }
    runtime_body = json.dumps(runtime_document).encode()
    state.add("/java/runtime.json", runtime_body)
    return state.add(
        "/java/all.json",
        json.dumps(
            {
                "linux": {
                    JAVA_COMPONENT: [
                        {
                            "manifest": remote(server.url("/java/runtime.json"), runtime_body),
                            "version": {"name": "8u999"},
                        }
                    ]
                }
            }
        ).encode(),
    )
