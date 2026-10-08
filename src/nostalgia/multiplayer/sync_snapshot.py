"""Chụp các thư mục modpack vào vùng tạm; không gửi saves, logs, tài khoản hay cache."""

from __future__ import annotations

import hashlib
from pathlib import Path

from nostalgia.errors import MultiplayerError
from nostalgia.modloader.model import LoaderKind
from nostalgia.multiplayer.sync_manifest import (
    MAX_SYNC_BYTES,
    MAX_SYNC_FILE_BYTES,
    MAX_SYNC_FILES,
    SYNC_DIRECTORIES,
    manifest_document,
    parse_sync_manifest,
    sync_path,
)
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.operations.cancellation import CancelToken


def capture_sync_snapshot(
    source: Path,
    destination: Path,
    *,
    name: str,
    game_version: str,
    loader_kind: LoaderKind,
    loader_version: str,
    cancel_token: CancelToken,
    excluded_mods: frozenset[str] = frozenset(),
) -> SyncSnapshot:
    if source.is_symlink():
        raise MultiplayerError("Không chia sẻ modpack từ liên kết thư mục.")
    files: list[SyncFile] = []
    total = 0
    excluded_mods = frozenset(value.removesuffix(".disabled") for value in excluded_mods)
    for directory in sorted(SYNC_DIRECTORIES):
        folder = source / directory
        if folder.is_symlink():
            raise MultiplayerError("Modpack có liên kết thư mục; chia sẻ đã dừng.")
        if not folder.exists():
            continue
        for parent, directories, names in folder.walk(follow_symlinks=False, on_error=_walk_error):
            if any((parent / child).is_symlink() for child in directories):
                raise MultiplayerError("Modpack có liên kết thư mục; chia sẻ đã dừng.")
            directories[:] = [child for child in directories if not child.startswith(".")]
            for name_on_disk in sorted(names):
                if name_on_disk.startswith("."):
                    continue
                cancel_token.raise_if_cancelled()
                path = parent / name_on_disk
                relative = sync_path(path.relative_to(source).as_posix())
                if directory == "mods" and relative.removesuffix(".disabled") in excluded_mods:
                    continue
                if (
                    path.is_symlink()
                    or not path.is_file()
                    or path.stat().st_size > MAX_SYNC_FILE_BYTES
                ):
                    raise MultiplayerError(
                        "Modpack có liên kết, file đặc biệt hoặc file quá 64 MiB."
                    )
                payload = path.read_bytes()
                total += len(payload)
                if (
                    len(payload) > MAX_SYNC_FILE_BYTES
                    or total > MAX_SYNC_BYTES
                    or len(files) >= MAX_SYNC_FILES
                ):
                    raise MultiplayerError("Modpack vượt giới hạn đồng bộ 1 GiB / 2.000 file.")
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                target.chmod(0o600)
                files.append(
                    SyncFile(
                        relative,
                        hashlib.sha256(payload).hexdigest(),
                        len(payload),
                        sha1=hashlib.sha1(payload).hexdigest(),
                    )
                )
    manifest = SyncManifest(name[:80], game_version, loader_kind, loader_version, tuple(files))
    return SyncSnapshot(parse_sync_manifest(manifest_document(manifest)), destination)


def _walk_error(error: OSError) -> None:
    raise error
