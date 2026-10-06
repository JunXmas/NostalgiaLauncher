"""Ảnh chụp modpack theo phòng; quyền Plus chỉ được quyết định ở máy chủ."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from nostalgia.modloader.model import LoaderKind
from nostalgia.operations.cancellation import CancelToken


@dataclass(frozen=True, slots=True)
class SyncFile:
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class SyncManifest:
    name: str
    game_version: str
    loader_kind: LoaderKind
    loader_version: str
    files: tuple[SyncFile, ...]

    @property
    def total_bytes(self) -> int:
        return sum(sync_file.size for sync_file in self.files)


@dataclass(frozen=True, slots=True)
class SyncSnapshot:
    manifest: SyncManifest
    folder: Path


class RoomSyncGateway(Protocol):
    def publish(
        self,
        room_code: str,
        host_ticket: str,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken | None = None,
    ) -> None: ...

    def resolve(self, room_code: str) -> SyncManifest | None: ...

    def download(self, room_code: str, sync_file: SyncFile) -> bytes: ...
