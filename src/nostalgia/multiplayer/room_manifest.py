"""Manifest dùng cho tính năng đồng bộ Rooms: build, diff, serialise."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from nostalgia.errors import UnsafePathError
from nostalgia.modloader.model import LoaderKind
from nostalgia.storage.files import resolve_within, sha1_of_file

logger = logging.getLogger(__name__)

MANIFEST_VERSION = 2
SCANNED_DIRS = ("mods", "config", "resourcepacks", "shaderpacks")


@dataclasses.dataclass(frozen=True, slots=True)
class FileEntry:
    """Một file trong manifest: đường dẫn tương đối + sha1."""

    relative_path: str
    sha1: str
    size: int


@dataclasses.dataclass(frozen=True, slots=True)
class Manifest:
    """Ảnh chụp trạng thái mods + config của một bản chơi."""

    manifest_version: int
    game_version: str
    loader_kind: str
    entries: tuple[FileEntry, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class ManifestDiff:
    """Khác biệt giữa hai manifest: cần tải + cần xoá."""

    to_download: tuple[FileEntry, ...]
    to_delete: tuple[str, ...]


def build_manifest(game_dir: Path, game_version: str, loader_kind: str) -> Manifest:
    """Quét mods/, config/, resourcepacks/, shaderpacks/ và băm từng file."""
    entries = []
    for scan_dir_name in SCANNED_DIRS:
        scan_dir = game_dir / scan_dir_name
        if not scan_dir.is_dir():
            continue
        for dir_root, dirs, files in os.walk(scan_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if filename.startswith("."):
                    continue
                file_path = Path(dir_root) / filename
                rel_path = file_path.relative_to(game_dir).as_posix()
                try:
                    resolve_within(game_dir, rel_path)
                except UnsafePathError:
                    logger.warning("Bỏ qua file không an toàn: %s", rel_path)
                    continue
                sha1 = sha1_of_file(file_path)
                file_size = file_path.stat().st_size
                entries.append(FileEntry(relative_path=rel_path, sha1=sha1, size=file_size))
    return Manifest(
        manifest_version=MANIFEST_VERSION,
        game_version=game_version,
        loader_kind=loader_kind,
        entries=tuple(entries),
    )


def diff_manifest(local: Manifest, remote: Manifest) -> ManifestDiff:
    """So manifest cục bộ với remote. Trả file cần tải và file cần xoá."""
    local_dict = {fe.relative_path: fe for fe in local.entries}
    remote_dict = {fe.relative_path: fe for fe in remote.entries}
    to_download = [
        remote_fe for path, remote_fe in remote_dict.items()
        if path not in local_dict or local_dict[path].sha1 != remote_fe.sha1
    ]
    to_delete = [path for path in local_dict if path not in remote_dict]
    return ManifestDiff(to_download=tuple(to_download), to_delete=tuple(to_delete))


def safe_paths_only(entries: tuple[FileEntry, ...], game_dir: Path) -> tuple[FileEntry, ...]:
    """Lọc chỉ giữ các entry có đường dẫn an toàn."""
    safe = []
    for fe in entries:
        try:
            resolve_within(game_dir, fe.relative_path)
            safe.append(fe)
        except UnsafePathError:
            logger.warning("Bỏ qua entry không an toàn: %s", fe.relative_path)
    return tuple(safe)


def manifest_to_dict(manifest: Manifest) -> dict[str, Any]:
    """Chuyển manifest thành dict để gửi qua relay dạng JSON."""
    return {
        "version": manifest.manifest_version,
        "game_version": manifest.game_version,
        "loader_kind": manifest.loader_kind,
        "entries": [
            {"relative_path": fe.relative_path, "sha1": fe.sha1, "size": fe.size}
            for fe in manifest.entries
        ],
    }


def manifest_from_dict(raw: dict[str, Any]) -> Manifest:
    """Đọc manifest từ dict nhận qua relay."""
    entries = tuple(
        FileEntry(
            relative_path=record["relative_path"],
            sha1=record["sha1"],
            size=record["size"],
        )
        for record in raw.get("entries", [])
    )
    return Manifest(
        manifest_version=raw.get("version", MANIFEST_VERSION),
        game_version=raw.get("game_version", ""),
        loader_kind=raw.get("loader_kind", ""),
        entries=entries,
    )


def _config_hash(game_dir: Path) -> str:
    """Băm tổng hợp thư mục config/ — dùng để so nhanh trước khi so chi tiết."""
    config_dir = game_dir / "config"
    if not config_dir.is_dir():
        return ""
    hasher = hashlib.sha1()
    paths = []
    for dir_root, dirs, files in os.walk(config_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if not filename.startswith("."):
                paths.append(Path(dir_root) / filename)
    paths.sort()
    for fpath in paths:
        try:
            rel_path = fpath.relative_to(game_dir).as_posix()
            hasher.update(rel_path.encode("utf-8"))
            with open(fpath, "rb") as fobj:
                while chunk := fobj.read(8192):
                    hasher.update(chunk)
        except Exception:
            logger.warning("Lỗi khi băm file %s", fpath, exc_info=True)
            continue
    return hasher.hexdigest()
