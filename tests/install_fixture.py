"""Dựng một bản cài giả đầy đủ trên đĩa, để `doctor` có thứ thật mà soi.

Ở gốc `tests/` cùng `version_fixtures.py`: đây là bộ dựng dữ liệu dùng chung, không phải
test. Nội dung file do chính đây sinh ra nên sha1 luôn khớp — điều kiện để kiểm được cả
đường băm lại, thứ mà fixture cắt từ Mojang không cho phép vì ta không có file thật.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from nostalgia.model.json_value import JsonValue
from nostalgia.storage.paths import DataPaths

CLIENT_BODY = b"noi dung client jar"
LIBRARY_BODY = b"noi dung thu vien"
ASSET_BODY = b"noi dung mot asset"
NATIVE_MEMBER = b"noi dung file .so"
VERSION_ID = "kiem-tra"


def digest(payload: bytes) -> str:
    return hashlib.sha1(payload).hexdigest()


def remote(payload: bytes, name: str) -> dict[str, JsonValue]:
    return {"url": f"https://mo/{name}", "sha1": digest(payload), "size": len(payload)}


def make_natives_zip(path: Path) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("linux/x64/libthu.so", NATIVE_MEMBER)
        archive.writestr("META-INF/MANIFEST.MF", b"bi loai")
    return path.read_bytes()


def build_install(tmp_path: Path) -> tuple[DataPaths, dict[str, JsonValue], dict[str, JsonValue]]:
    """Dựng một bản cài đầy đủ và trả về (paths, version_dict, asset_index_document)."""
    paths = DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")

    natives_path = paths.libraries_dir / "org/thu/nat/1.0/nat-1.0-natives-linux.jar"
    natives_body = make_natives_zip(natives_path)

    version_dict: dict[str, JsonValue] = {
        "id": VERSION_ID,
        "mainClass": "Main",
        "assets": "kt",
        "downloads": {"client": remote(CLIENT_BODY, "client")},
        "assetIndex": {"id": "kt", **remote(b"", "index")},
        "libraries": [
            {
                "name": "org.thu:vien:1.0",
                "downloads": {
                    "artifact": {
                        "path": "org/thu/vien/1.0/vien-1.0.jar",
                        **remote(LIBRARY_BODY, "vien"),
                    }
                },
            },
            {
                "name": "org.thu:nat:1.0",
                "natives": {"linux": "natives-linux"},
                "downloads": {
                    "classifiers": {
                        "natives-linux": {
                            "path": "org/thu/nat/1.0/nat-1.0-natives-linux.jar",
                            **remote(natives_body, "nat"),
                        }
                    }
                },
            },
        ],
    }

    asset_hash = digest(ASSET_BODY)
    index_document: dict[str, JsonValue] = {
        "objects": {"minecraft/am.ogg": {"hash": asset_hash, "size": len(ASSET_BODY)}}
    }
    index_body = json.dumps(index_document).encode()
    version_dict["assetIndex"] = {"id": "kt", **remote(index_body, "index")}

    _write(paths.version_jar(VERSION_ID), CLIENT_BODY)
    _write(paths.libraries_dir / "org/thu/vien/1.0/vien-1.0.jar", LIBRARY_BODY)
    _write(paths.natives_dir(VERSION_ID) / "libthu.so", NATIVE_MEMBER)
    _write(paths.asset_index_json("kt"), index_body)
    _write(paths.asset_object(asset_hash), ASSET_BODY)
    return paths, version_dict, index_document


def _write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
