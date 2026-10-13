"""Track only bundled files; player settings and privately added mods remain unowned."""

import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from nostalgia.content.mrpack import ModpackIndex
from nostalgia.errors import ContentError
from nostalgia.model.json_value import JsonValue, as_mapping, as_string
from nostalgia.multiplayer.sync_manifest import SYNC_DIRECTORIES, sync_path
from nostalgia.storage.files import atomic_write_json, read_json

RECEIPT_FILE = ".nostalgia-builtin-pack.json"
PACK_MARKER = "README-Forgotten-Worlds.txt"


def bundle_version(pack_path: Path) -> str:
    with zipfile.ZipFile(pack_path) as archive:
        document = as_mapping(json.loads(archive.read("modrinth.index.json")))
    return as_string(document.get("versionId")) or "unknown"


@dataclass(frozen=True, slots=True)
class BundledFile:
    sha1: str
    identity: str


@dataclass(frozen=True, slots=True)
class BuiltinReceipt:
    version: str
    files: dict[str, BundledFile]


def bundle_receipt(pack_path: Path, index: ModpackIndex) -> BuiltinReceipt:
    owned: dict[str, BundledFile] = {}
    for entry in index.files:
        relative = sync_path(entry.relative_path)
        parts = urlsplit(entry.url).path.split("/")
        identity = (
            "project:" + parts[2]
            if urlsplit(entry.url).hostname == "cdn.modrinth.com" and len(parts) > 3
            else "path:" + relative
        )
        owned[relative] = BundledFile(entry.sha1, identity)
    with zipfile.ZipFile(pack_path) as archive:
        document = as_mapping(json.loads(archive.read("modrinth.index.json")))
        for prefix in ("overrides/", "client-overrides/"):
            for member in archive.infolist():
                if not member.filename.startswith(prefix) or member.is_dir():
                    continue
                relative = member.filename[len(prefix) :]
                if relative.split("/")[0] not in SYNC_DIRECTORIES:
                    continue
                relative = sync_path(relative)
                owned[relative] = BundledFile(
                    hashlib.sha1(archive.read(member)).hexdigest(), "path:" + relative
                )
    return BuiltinReceipt(as_string(document.get("versionId")) or "unknown", owned)


def load_builtin_receipt(registry_dir: Path) -> BuiltinReceipt | None:
    path = registry_dir / RECEIPT_FILE
    if not path.exists():
        return None
    if path.is_symlink() or path.stat().st_size > 2 * 1024**2:
        raise ContentError("Dấu vết modpack không an toàn.")
    document = as_mapping(read_json(path))
    if document.get("format") != 1 or document.get("preset") != "forgotten-worlds":
        raise ContentError("Không nhận diện được dấu vết modpack.")
    return parse_receipt(document)


def parse_receipt(document: dict[str, JsonValue]) -> BuiltinReceipt:
    version = as_string(document.get("version"))
    if not version or len(version) > 96:
        raise ContentError("Dấu vết modpack thiếu phiên bản.")
    owned: dict[str, BundledFile] = {}
    for relative, raw in as_mapping(document.get("files")).items():
        entry = as_mapping(raw)
        digest, identity = as_string(entry.get("sha1")), as_string(entry.get("identity"))
        if not digest or not re.fullmatch(r"[0-9a-f]{40}", digest) or not identity:
            raise ContentError("Dấu vết file modpack không hợp lệ.")
        owned[sync_path(relative)] = BundledFile(digest, identity)
    return BuiltinReceipt(version, owned)


def save_builtin_receipt(registry_dir: Path, receipt: BuiltinReceipt) -> None:
    owned: dict[str, JsonValue] = {
        relative: {"sha1": entry.sha1, "identity": entry.identity}
        for relative, entry in receipt.files.items()
    }
    atomic_write_json(
        registry_dir / RECEIPT_FILE,
        {"format": 1, "preset": "forgotten-worlds", "version": receipt.version, "files": owned},
        private=True,
    )


def legacy_receipt() -> BuiltinReceipt:
    path = files("nostalgia.content") / "packs" / "forgotten-worlds-legacy-files.json"
    return parse_receipt(as_mapping(json.loads(path.read_text(encoding="utf-8"))))


def legacy_pack_version(game_dir: Path) -> str:
    marker = game_dir / PACK_MARKER
    if marker.is_symlink() or not marker.is_file() or marker.stat().st_size > 65536:
        return ""
    try:
        first = marker.read_text(encoding="utf-8").splitlines()[0]
    except (OSError, UnicodeError, IndexError):
        return ""
    prefix = "Forgotten Worlds — Optimized "
    return first.removeprefix(prefix).strip() if first.startswith(prefix) else ""
