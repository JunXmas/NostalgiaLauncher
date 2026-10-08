"""Cập nhật đúng instance đã nhận: tải phần đổi, giữ file riêng và thế giới của khách."""

import tempfile
from dataclasses import replace
from pathlib import Path

from nostalgia.errors import MultiplayerError
from nostalgia.facade.sync_review import SyncReviewOperations
from nostalgia.facade.sync_source import matches_sync_file
from nostalgia.instance.model import Instance
from nostalgia.instance.store import game_dir_of, load_instance, save_instance
from nostalgia.instance.sync_receipt import load_sync_receipt, save_sync_receipt
from nostalgia.instance.sync_transaction import (
    recover_sync_update,
    replace_sync_bytes,
    safe_sync_target,
    sync_transaction,
)
from nostalgia.multiplayer.sync_model import RoomSyncGateway, SyncManifest
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn
from nostalgia.storage.files import sync_directory
from nostalgia.storage.sync_lock import sync_lock


def sync_variants(relative_path: str) -> frozenset[str]:
    if relative_path.split("/")[0] in ("mods", "resourcepacks", "shaderpacks"):
        canonical = relative_path.removesuffix(".disabled")
        return frozenset({canonical, canonical + ".disabled"})
    return frozenset({relative_path})


class SyncUpdateOperations(SyncReviewOperations):
    __slots__ = ()

    def update_room_modpack(
        self,
        gateway: RoomSyncGateway,
        room_code: str,
        original: SyncManifest,
        manifest: SyncManifest,
        instance: Instance,
        excluded_paths: frozenset[str],
        *,
        cancel_token: CancelToken,
        on_progress: ProgressFn,
    ) -> Instance:
        registry_dir = self.paths.instance_dir(instance.instance_id)
        game_dir = game_dir_of(self.paths, instance)
        with sync_lock(registry_dir):
            recover_sync_update(registry_dir, game_dir)
            instance = load_instance(self.paths, instance.instance_id)
            receipt = load_sync_receipt(self.paths, instance.instance_id)
            if receipt is None or (receipt.owner_id, receipt.pack_id) != (
                original.owner_id,
                original.pack_id,
            ):
                raise MultiplayerError("Bản chơi đã thay đổi dấu vết; cập nhật đã dừng.")
            managed = frozenset(
                path
                for sync_file in receipt.files
                for path in sync_variants(sync_file.relative_path)
            )
            desired = {sync_file.relative_path: sync_file for sync_file in manifest.files}
            desired_variants = frozenset(
                path for relative_path in desired for path in sync_variants(relative_path)
            )
            for relative_path in managed | desired_variants:
                target = safe_sync_target(game_dir, relative_path)
                if relative_path not in managed and target.exists():
                    raise MultiplayerError(
                        "File khách tự thêm trùng với host: "
                        + relative_path
                        + ". Hãy đổi tên hoặc chuyển file đó trước khi đồng bộ."
                    )
            with tempfile.TemporaryDirectory(
                prefix="room-update-", dir=self.paths.instances_dir
            ) as temporary:
                stage = Path(temporary)
                reused_paths = frozenset(
                    sync_file.relative_path
                    for sync_file in manifest.files
                    if matches_sync_file(
                        safe_sync_target(game_dir, sync_file.relative_path), sync_file
                    )
                )
                self.sync_room_files(
                    gateway,
                    room_code,
                    manifest,
                    stage,
                    cancel_token=cancel_token,
                    on_progress=on_progress,
                    install_base=False,
                    reused_paths=reused_paths,
                )
                report = self.install_loader(
                    manifest.loader_kind,
                    manifest.game_version,
                    manifest.loader_version or None,
                    cancel_token=cancel_token,
                    on_progress=on_progress,
                )
                cancel_token.raise_if_cancelled()
                if gateway.resolve(room_code) != original:
                    raise MultiplayerError(
                        "Modpack của host đã thay đổi; mở lại lựa chọn để cập nhật."
                    )
                changed = frozenset(
                    relative_path
                    for relative_path in managed | desired_variants
                    if (
                        relative_path in desired
                        and not matches_sync_file(
                            safe_sync_target(game_dir, relative_path), desired[relative_path]
                        )
                    )
                    or (
                        relative_path not in desired
                        and safe_sync_target(game_dir, relative_path).exists()
                    )
                )
                if any(relative_path in reused_paths for relative_path in changed):
                    raise MultiplayerError(
                        "File đã thay đổi trong lúc đồng bộ; hãy thử lại sau khi đóng game."
                    )
                current = load_instance(self.paths, instance.instance_id)
                if game_dir_of(self.paths, current) != game_dir:
                    raise MultiplayerError("Thư mục bản chơi đã thay đổi; cập nhật đã dừng.")
                for relative_path in desired_variants - managed:
                    if safe_sync_target(game_dir, relative_path).exists():
                        raise MultiplayerError(
                            "File riêng mới xuất hiện trùng với host: " + relative_path
                        )
                updated = replace(current, version_id=report.version_meta.version_id)
                with sync_transaction(registry_dir, game_dir, changed):
                    for relative_path in sorted(changed):
                        cancel_token.raise_if_cancelled()
                        target = safe_sync_target(game_dir, relative_path)
                        if relative_path in desired:
                            replace_sync_bytes(stage / relative_path, target)
                        else:
                            target.unlink(missing_ok=True)
                            sync_directory(target.parent)
                    cancel_token.raise_if_cancelled()
                    save_instance(self.paths, updated)
                    save_sync_receipt(self.paths, updated.instance_id, manifest, excluded_paths)
                return updated
