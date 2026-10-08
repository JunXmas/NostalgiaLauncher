"""Ghi nguồn và mã băm ngay sau cài pack; thay đổi sau đó được so với bản gốc này."""

import hashlib
from pathlib import Path

from nostalgia.content.pack_reference import parse_pack_reference, reference_document
from nostalgia.errors import NostalgiaError
from nostalgia.model.json_value import JsonValue, as_list, as_mapping
from nostalgia.model.pack import PackFile, PackOrigin, PackReference
from nostalgia.multiplayer.sync_manifest import SYNC_DIRECTORIES, sync_path
from nostalgia.storage.files import atomic_write_json, read_json

ORIGIN_FILE = ".nostalgia-pack-origin.json"


def save_pack_origin(
    game_dir: Path,
    reference: PackReference,
    game_version: str,
    loader_kind: str,
    loader_version: str,
) -> None:
    files: list[JsonValue] = []
    for directory in sorted(SYNC_DIRECTORIES):
        folder = game_dir / directory
        if not folder.is_dir() or folder.is_symlink():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(game_dir).as_posix()
            if any(part.startswith(".") for part in path.relative_to(game_dir).parts):
                continue
            relative = sync_path(relative)
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            files.append({"path": relative, "sha256": digest, "size": path.stat().st_size})
    atomic_write_json(
        game_dir / ORIGIN_FILE,
        {
            "format": 1,
            "reference": reference_document(reference),
            "game_version": game_version,
            "loader_kind": loader_kind,
            "loader_version": loader_version,
            "files": files,
        },
        private=True,
    )


def load_pack_origin(game_dir: Path) -> PackOrigin | None:
    path = game_dir / ORIGIN_FILE
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 2 * 1024**2:
        return None
    try:
        fields = as_mapping(read_json(path))
        if fields.get("format") != 1:
            return None
        reference = parse_pack_reference(fields.get("reference"))
        game_version, loader_kind = fields["game_version"], fields["loader_kind"]
        loader_version = fields["loader_version"]
        if not all(isinstance(value, str) for value in (game_version, loader_kind, loader_version)):
            return None
        files: list[PackFile] = []
        for raw in as_list(fields.get("files")):
            pack_entry = as_mapping(raw)
            relative, digest, size = pack_entry["path"], pack_entry["sha256"], pack_entry["size"]
            if (
                not isinstance(relative, str)
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(letter not in "0123456789abcdef" for letter in digest)
                or type(size) is not int
                or size < 0
            ):
                return None
            files.append(PackFile(sync_path(relative), digest, size))
        if (
            isinstance(game_version, str)
            and isinstance(loader_kind, str)
            and isinstance(loader_version, str)
        ):
            return PackOrigin(reference, game_version, loader_kind, loader_version, tuple(files))
    except (NostalgiaError, KeyError, ValueError, OSError):
        return None
    return None
