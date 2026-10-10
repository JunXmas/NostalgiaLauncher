"""Chia sẻ ảnh chụp pack; khách chọn nội dung, tạo bản riêng hoặc cập nhật đúng dấu vết."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from dataclasses import replace
from pathlib import Path

from nostalgia.errors import MultiplayerError
from nostalgia.facade.sync_loader import resolve_sync_loader
from nostalgia.facade.sync_review import OPTIONAL_DIRECTORIES
from nostalgia.facade.sync_update import SyncUpdateOperations
from nostalgia.instance.model import Instance
from nostalgia.instance.store import create_instance, game_dir_of, load_instance
from nostalgia.instance.sync_identity import ensure_sync_pack_id
from nostalgia.instance.sync_receipt import save_sync_receipt
from nostalgia.modloader.model import detect_loader_kind
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.sync_manifest import manifest_document, parse_sync_manifest, sync_path
from nostalgia.multiplayer.sync_model import RoomSyncGateway, SyncManifest, SyncSnapshot
from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.storage.sync_lock import sync_lock


class RoomSyncOperations(SyncUpdateOperations):
    __slots__ = ()

    def publish_room_modpack(
        self,
        gateway: RoomSyncGateway,
        status: RoomStatus,
        instance_id: str,
        *,
        cancel_token: CancelToken,
    ) -> None:
        if status.role != "hosting" or not status.host_ticket:
            raise MultiplayerError("Relay chưa cấp vé xác thực chủ phòng; chưa thể chia sẻ Plus.")
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="room-publish-", dir=self.paths.data_dir
        ) as temporary:
            snapshot = self.capture_room_modpack(
                instance_id, Path(temporary), cancel_token=cancel_token
            )
            self.publish_room_snapshot(gateway, status, snapshot, cancel_token=cancel_token)

    def capture_room_modpack(
        self,
        instance_id: str,
        folder: Path,
        *,
        cancel_token: CancelToken,
        excluded_mods: frozenset[str] = frozenset(),
    ) -> SyncSnapshot:
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        loader_kind = detect_loader_kind(instance.version_id)
        game_dir = game_dir_of(self.paths, instance)
        snapshot = capture_sync_snapshot(
            game_dir,
            folder,
            name=instance.label,
            game_version=version_meta.jar_owner_id,
            loader_kind=loader_kind,
            loader_version=resolve_sync_loader(
                loader_kind,
                version_meta.libraries,
                version_meta.jar_owner_id,
                game_arguments=version_meta.game_arguments,
            ),
            cancel_token=cancel_token,
            excluded_mods=excluded_mods,
        )
        snapshot = replace(
            snapshot,
            manifest=replace(
                snapshot.manifest, pack_id=ensure_sync_pack_id(self.paths, instance_id)
            ),
        )
        return self.describe_sync_snapshot(game_dir, snapshot)

    def publish_room_snapshot(
        self,
        gateway: RoomSyncGateway,
        status: RoomStatus,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken,
    ) -> None:
        if status.role != "hosting" or not status.host_ticket:
            raise MultiplayerError("Relay chưa cấp vé xác thực chủ phòng; chưa thể chia sẻ Plus.")
        cancel_token.raise_if_cancelled()
        gateway.publish(status.room_code, status.host_ticket, snapshot, cancel_token=cancel_token)

    def sync_room_modpack(
        self,
        gateway: RoomSyncGateway,
        room_code: str,
        manifest: SyncManifest,
        *,
        cancel_token: CancelToken,
        on_progress: ProgressFn = ignore_progress,
        excluded_paths: frozenset[str] = frozenset(),
    ) -> Instance:
        with sync_lock(self.paths.data_dir / ".nostalgia-room-sync"):
            return self._sync_room_modpack(
                gateway,
                room_code,
                manifest,
                cancel_token=cancel_token,
                on_progress=on_progress,
                excluded_paths=excluded_paths,
            )

    def _sync_room_modpack(
        self,
        gateway: RoomSyncGateway,
        room_code: str,
        manifest: SyncManifest,
        *,
        cancel_token: CancelToken,
        on_progress: ProgressFn = ignore_progress,
        excluded_paths: frozenset[str] = frozenset(),
    ) -> Instance:
        manifest = parse_sync_manifest(manifest_document(manifest))
        if gateway.resolve(room_code) != manifest:
            raise MultiplayerError("Modpack của phòng đã thay đổi. Hãy mở lại thông tin đồng bộ.")
        original = manifest
        excluded_paths = frozenset(
            sync_path(path).removesuffix(".disabled") for path in excluded_paths
        )
        if any(path.split("/")[0] not in OPTIONAL_DIRECTORIES for path in excluded_paths):
            raise MultiplayerError("Chỉ có thể bỏ chọn mods, texture pack hoặc shader pack.")
        manifest = replace(
            manifest,
            files=tuple(
                sync_file
                for sync_file in manifest.files
                if sync_file.relative_path.removesuffix(".disabled") not in excluded_paths
            ),
        )
        self.paths.instances_dir.mkdir(parents=True, exist_ok=True)
        existing = self.matched_room_instance(original)
        if existing is not None:
            return self.update_room_modpack(
                gateway,
                room_code,
                original,
                manifest,
                existing,
                excluded_paths,
                cancel_token=cancel_token,
                on_progress=on_progress,
            )
        instance_id = "room-" + uuid.uuid4().hex[:16]
        destination = self.paths.instance_dir(instance_id)
        with tempfile.TemporaryDirectory(
            prefix="room-download-", dir=self.paths.instances_dir
        ) as temporary:
            stage = Path(temporary) / "game"
            stage.mkdir()
            self.sync_room_files(
                gateway,
                room_code,
                manifest,
                stage,
                cancel_token=cancel_token,
                on_progress=on_progress,
            )
            cancel_token.raise_if_cancelled()
            report = self.install_loader(
                manifest.loader_kind,
                manifest.game_version,
                manifest.loader_version or None,
                cancel_token=cancel_token,
                on_progress=on_progress,
            )
            cancel_token.raise_if_cancelled()
            instance = Instance(
                instance_id, report.version_meta.version_id, manifest.name + " · Chơi chung"
            )
            if gateway.resolve(room_code) != original:
                raise MultiplayerError("Modpack của host đã thay đổi; mở lại lựa chọn để đồng bộ.")
            stage.rename(destination)
            try:
                created = create_instance(self.paths, instance)
                save_sync_receipt(self.paths, instance_id, manifest, excluded_paths)
                return created
            except Exception:
                shutil.rmtree(destination)
                raise
