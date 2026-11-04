"""Kiểm tra jar trước khi thay cache: mã mod, Minecraft, toàn vẹn ZIP và SHA-256."""

from __future__ import annotations

import hashlib
import json
import zipfile
import zlib
from pathlib import Path

from nostalgia.modcheck.predicate import matches_any
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.nos_client.compatibility import SUPPORTED_GAME_VERSIONS
from nostalgia.nos_client.release import MAX_JAR_BYTES


def load_nos_version(path: Path) -> str:
    """Đọc metadata nhỏ để nhận cả jar Nos đã được người chơi đổi tên."""
    try:
        if path.is_symlink():
            return ""
        with zipfile.ZipFile(path) as jar:
            member = jar.getinfo("fabric.mod.json")
            if member.file_size > 64 * 1024:
                return ""
            document: JsonValue = json.loads(jar.read(member))
            mod = as_mapping(document)
            return (as_string(mod.get("version")) or "") if mod.get("id") == "nosclient" else ""
    except (
        OSError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
        zlib.error,
        EOFError,
    ):
        return ""


def verify_mod_artifact(
    path: Path,
    game_version: str,
    *,
    sha256: str | None = None,
    size: int | None = None,
    mod_version: str = "",
    loader_version: str = "",
) -> bool:
    """Chỉ nhận dependency Minecraft chính xác; bản phát hành của Nos luôn ghim API này."""
    if game_version not in SUPPORTED_GAME_VERSIONS:
        return False
    try:
        if path.is_symlink():
            return False
        actual_size = path.stat().st_size
        if not 0 < actual_size <= MAX_JAR_BYTES or (size is not None and actual_size != size):
            return False
        if sha256 is not None:
            with path.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != sha256:
                    return False
        with zipfile.ZipFile(path) as jar:
            entries = jar.infolist()
            if sum(member.file_size for member in entries) > MAX_JAR_BYTES * 4:
                return False
            if sum(member.filename == "fabric.mod.json" for member in entries) != 1:
                return False
            metadata = jar.getinfo("fabric.mod.json")
            if metadata.file_size > 64 * 1024 or jar.testzip() is not None:
                return False
            document: JsonValue = json.loads(jar.read(metadata))
            mod = as_mapping(document)
            dependencies = as_mapping(mod.get("depends"))
            dependency = dependencies.get("minecraft")
            if mod_version and mod.get("version") != mod_version:
                return False
            for mod_id, installed in (("fabricloader", loader_version), ("java", "21")):
                required = dependencies.get(mod_id)
                if not installed or required is None:
                    continue
                predicates = (
                    (required,)
                    if isinstance(required, str)
                    else tuple(value for value in required if isinstance(value, str))
                    if isinstance(required, list)
                    else ()
                )
                if matches_any(installed, predicates) is not True:
                    return False
            return mod.get("id") == "nosclient" and (
                dependency == game_version or dependency == [game_version]
            )
    except (
        OSError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
        zlib.error,
        EOFError,
    ):
        return False
