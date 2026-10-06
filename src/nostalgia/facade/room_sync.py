"""Chia sẻ ảnh chụp pack và cài vào bản chơi mới; không ghi đè pack của khách."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import uuid
from pathlib import Path

from nostalgia.errors import MultiplayerError
from nostalgia.facade.loaders import LoaderOperations
from nostalgia.instance.model import Instance
from nostalgia.instance.store import create_instance, game_dir_of, load_instance
from nostalgia.modloader.model import LoaderKind, detect_loader_kind
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.sync_manifest import manifest_document, parse_sync_manifest
from nostalgia.multiplayer.sync_model import RoomSyncGateway, SyncManifest
from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.version.meta import Library


class RoomSyncOperations(LoaderOperations):
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
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        loader_kind = detect_loader_kind(instance.version_id)
        loader_version = _loader_version(
            loader_kind, version_meta.libraries, version_meta.jar_owner_id
        )
        self.paths.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="room-publish-", dir=self.paths.data_dir
        ) as temporary:
            snapshot = capture_sync_snapshot(
                game_dir_of(self.paths, instance),
                Path(temporary),
                name=instance.label,
                game_version=version_meta.jar_owner_id,
                loader_kind=loader_kind,
                loader_version=loader_version,
                cancel_token=cancel_token,
            )
            cancel_token.raise_if_cancelled()
            gateway.publish(
                status.room_code, status.host_ticket, snapshot, cancel_token=cancel_token
            )

    def sync_room_modpack(
        self,
        gateway: RoomSyncGateway,
        room_code: str,
        manifest: SyncManifest,
        *,
        cancel_token: CancelToken,
        on_progress: ProgressFn = ignore_progress,
    ) -> Instance:
        manifest = parse_sync_manifest(manifest_document(manifest))
        if gateway.resolve(room_code) != manifest:
            raise MultiplayerError("Modpack của phòng đã thay đổi. Hãy mở lại thông tin đồng bộ.")
        self.paths.instances_dir.mkdir(parents=True, exist_ok=True)
        instance_id = "room-" + uuid.uuid4().hex[:16]
        destination = self.paths.instance_dir(instance_id)
        with tempfile.TemporaryDirectory(
            prefix="room-download-", dir=self.paths.instances_dir
        ) as temporary:
            stage = Path(temporary) / "game"
            stage.mkdir()
            for sync_file in manifest.files:
                cancel_token.raise_if_cancelled()
                payload = gateway.download(room_code, sync_file)
                if (
                    len(payload) != sync_file.size
                    or hashlib.sha256(payload).hexdigest() != sync_file.sha256
                ):
                    raise MultiplayerError("File modpack không khớp SHA-256; đồng bộ đã dừng.")
                target = stage / sync_file.relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                target.chmod(0o600)
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
            stage.rename(destination)
            try:
                return create_instance(self.paths, instance)
            except Exception:
                shutil.rmtree(destination)
                raise


def _loader_version(
    loader_kind: LoaderKind, libraries: tuple[Library, ...], game_version: str
) -> str:
    # Chỉ nhận phiên bản từ tọa độ loader đã cài; không chuyển JSON/classpath của host sang khách.
    if loader_kind == "vanilla":
        return ""
    artifact_names = {
        "fabric": "fabric-loader",
        "quilt": "quilt-loader",
        "forge": "forge",
        "neoforge": "neoforge",
    }
    for library in libraries:
        if library.coordinate.artifact == artifact_names[loader_kind]:
            return (
                library.coordinate.artifact_version.removeprefix(game_version + "-")
                if loader_kind == "forge"
                else library.coordinate.artifact_version
            )
    raise MultiplayerError("Không tìm thấy phiên bản loader. Hãy cài lại loader trước khi chia sẻ.")
