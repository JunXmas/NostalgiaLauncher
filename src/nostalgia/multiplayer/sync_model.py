"""Ảnh chụp modpack theo phòng; quyền Plus chỉ được quyết định ở máy chủ."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from nostalgia.model.pack import PackReference
from nostalgia.modloader.model import LoaderKind
from nostalgia.operations.cancellation import CancelToken


@dataclass(frozen=True, slots=True)
class SyncFile:
    relative_path: str
    sha256: str
    size: int
    source: PackReference | None = None
    from_base: bool = False
    sha1: str = ""
    title: str = ""
    icon_url: str = ""


@dataclass(frozen=True, slots=True)
class SyncManifest:
    name: str
    game_version: str
    loader_kind: LoaderKind
    loader_version: str
    files: tuple[SyncFile, ...]
    base_pack: PackReference | None = None
    pack_id: str = ""
    owner_id: str = ""

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
