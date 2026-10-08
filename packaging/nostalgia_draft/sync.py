"""Disk-backed local transport for testing the real snapshot/install/hash pipeline."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import replace
from pathlib import Path

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.sync_manifest import manifest_document, parse_sync_manifest
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.operations.cancellation import CancelToken


class ReviewSync:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self._manifest: SyncManifest | None = None
        self._room = ""

    def publish(
        self,
        room_code: str,
        host_ticket: str,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken | None = None,
    ) -> None:
        del host_ticket
        manifest = parse_sync_manifest(manifest_document(snapshot.manifest))
        # Bài thử nội bộ chỉ dùng bản cache trên đĩa, không truy vấn nguồn công khai.
        manifest = replace(
            manifest,
            base_pack=None,
            files=tuple(
                replace(sync_file, sha1="", source=None, from_base=False)
                for sync_file in manifest.files
            ),
        )
        self.directory.mkdir(parents=True, exist_ok=True)
        for sync_file in manifest.files:
            if cancel_token:
                cancel_token.raise_if_cancelled()
            source = snapshot.folder / sync_file.relative_path
            destination = self.directory / sync_file.relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            with destination.open("rb") as stream:
                if (
                    destination.stat().st_size != sync_file.size
                    or hashlib.file_digest(stream, "sha256").hexdigest() != sync_file.sha256
                ):
                    raise MultiplayerError("Bản chụp TEST đổi trong lúc sao chép.")
        self._room, self._manifest = room_code, manifest

    def resolve(self, room_code: str) -> SyncManifest | None:
        return self._manifest if room_code == self._room else None

    def download(self, room_code: str, sync_file: SyncFile) -> bytes:
        if room_code != self._room or not self._manifest or sync_file not in self._manifest.files:
            raise MultiplayerError("File không thuộc bản chụp TEST.")
        return (self.directory / sync_file.relative_path).read_bytes()
