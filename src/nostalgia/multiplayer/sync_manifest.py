"""Kiểm dữ liệu nhận từ phòng trước khi tải/ghi; không chấp nhận đường dẫn tùy ý."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from nostalgia.errors import MultiplayerError
from nostalgia.model.json_value import JsonValue
from nostalgia.modloader.model import LOADER_KINDS
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest

MAX_SYNC_BYTES = 1024**3
MAX_SYNC_FILE_BYTES = 64 * 1024**2
MAX_SYNC_FILES = 2000
SYNC_DIRECTORIES = frozenset(
    {"mods", "config", "defaultconfigs", "kubejs", "scripts", "resourcepacks", "shaderpacks"}
)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_RESERVED = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z", re.I)


def sync_path(text: str) -> str:
    parts = PurePosixPath(text).parts
    if (
        not 1 < len(parts) <= 16
        or parts[0] not in SYNC_DIRECTORIES
        or len(text) > 240
        or text != "/".join(parts)
        or any(ord(char) < 32 or char in '\\:*?"<>|' for char in text)
        or any(
            part in (".", "..") or part.endswith((".", " ")) or _RESERVED.fullmatch(part)
            for part in parts
        )
        or any(part.startswith(".") for part in parts)
    ):
        raise MultiplayerError(
            "Modpack có đường dẫn không an toàn hoặc ngoài thư mục được chia sẻ."
        )
    return text


def parse_sync_manifest(document: JsonValue) -> SyncManifest:
    try:
        if not isinstance(document, dict) or document.get("format") != 1:
            raise ValueError
        name = document["name"]
        game_version = document["game_version"]
        loader_kind = document["loader_kind"]
        loader_version = document["loader_version"]
        entries = document["files"]
        if (
            not isinstance(name, str)
            or not 1 <= len(name) <= 80
            or any(ord(char) < 32 for char in name)
            or any(char in "<>" for char in name)
            or not isinstance(game_version, str)
            or not _IDENTIFIER.fullmatch(game_version)
            or not isinstance(loader_kind, str)
            or loader_kind not in LOADER_KINDS
            or not isinstance(loader_version, str)
            or (loader_kind != "vanilla" and not _IDENTIFIER.fullmatch(loader_version))
            or (loader_kind == "vanilla" and loader_version != "")
            or not isinstance(entries, list)
            or not 1 <= len(entries) <= MAX_SYNC_FILES
        ):
            raise ValueError
        files: list[SyncFile] = []
        seen: set[str] = set()
        for sync_entry in entries:
            if not isinstance(sync_entry, dict):
                raise ValueError
            path, digest, size = sync_entry["path"], sync_entry["sha256"], sync_entry["size"]
            if (
                not isinstance(path, str)
                or not isinstance(digest, str)
                or not _HASH.fullmatch(digest)
                or type(size) is not int
                or not 0 <= size <= MAX_SYNC_FILE_BYTES
            ):
                raise ValueError
            path = sync_path(path)
            if path.casefold() in seen:
                raise ValueError
            seen.add(path.casefold())
            files.append(SyncFile(path, digest, size))
        if sum(sync_file.size for sync_file in files) > MAX_SYNC_BYTES:
            raise ValueError
        for path in seen:
            parts = path.split("/")
            if any("/".join(parts[:depth]) in seen for depth in range(1, len(parts))):
                raise ValueError
        return SyncManifest(name, game_version, loader_kind, loader_version, tuple(files))
    except (KeyError, ValueError, TypeError):
        raise MultiplayerError(
            "Thông tin đồng bộ modpack không hợp lệ hoặc vượt giới hạn."
        ) from None


def manifest_document(manifest: SyncManifest) -> dict[str, JsonValue]:
    return {
        "format": 1,
        "name": manifest.name,
        "game_version": manifest.game_version,
        "loader_kind": manifest.loader_kind,
        "loader_version": manifest.loader_version,
        "files": [
            {"path": sync_file.relative_path, "sha256": sync_file.sha256, "size": sync_file.size}
            for sync_file in manifest.files
        ],
    }
