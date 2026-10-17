"""Update the bundled server pack in its existing instance, with rollback and backups."""

import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

from nostalgia.content.builtin_pack import load_forgotten_worlds_pack
from nostalgia.content.builtin_receipt import (
    bundle_receipt,
    bundle_version,
    legacy_pack_version,
    legacy_receipt,
    load_builtin_receipt,
    save_builtin_receipt,
)
from nostalgia.content.builtin_update import existing_variant, matches, plan_builtin_update
from nostalgia.content.mrpack import ALLOWED_HOSTS, read_index
from nostalgia.content.pack_channel import channel_pack, newer_channel, refresh_channel
from nostalgia.errors import ContentError, NetworkError, NostalgiaError
from nostalgia.facade.modpacks import ModpackOperations
from nostalgia.instance.model import Instance
from nostalgia.instance.store import load_instance
from nostalgia.instance.sync_transaction import (
    recover_sync_update,
    replace_sync_bytes,
    safe_sync_target,
    sync_transaction,
)
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_all
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import sync_directory
from nostalgia.storage.sync_lock import sync_lock
from nostalgia.update.release import is_newer

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BuiltinPackStatus:
    installed_version: str
    available_version: str

    @property
    def update_available(self) -> bool:
        return is_newer(self.available_version, self.installed_version)


class PresetUpdateOperations(ModpackOperations):
    __slots__ = ()

    def builtin_pack_status(self, instance: Instance) -> BuiltinPackStatus | None:
        game_dir = self.instance_game_dir(instance)
        receipt = load_builtin_receipt(self.paths.instance_dir(instance.instance_id))
        version_id = receipt.version_id if receipt is not None else legacy_pack_version(game_dir)
        if not version_id:
            return None
        pack_path = load_forgotten_worlds_pack()
        channel = newer_channel(self.paths, pack_path)
        latest = channel.version_id if channel else bundle_version(pack_path)
        return BuiltinPackStatus(version_id, latest)

    def refresh_builtin_modpack(self) -> None:
        """Check the server pack channel independently from launcher releases. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            refresh_channel(self.paths, http_client, self.endpoints.builtin_modpack_feed)

    def latest_builtin_pack(
        self,
        bundled_pack: Path,
        allowed_hosts: tuple[str, ...] | None = None,
        cancel_token: CancelToken | None = None,
    ) -> Path:
        with self.make_http_client() as http_client:
            # Hỏi lại kênh ngay lúc tải: bản đệm có thể trỏ vào release đã gỡ (404).
            # Mất mạng thì dùng bản đệm, lỗi tải sẽ báo ở bước sau.
            try:
                refresh_channel(
                    self.paths, http_client, self.endpoints.builtin_modpack_feed, cancel_token
                )
            except NostalgiaError as error:
                logger.warning("Không hỏi lại được kênh modpack, dùng bản đệm: %s", error)
            channel = newer_channel(self.paths, bundled_pack)
            if channel is None:
                return bundled_pack
            return channel_pack(
                self.paths,
                channel,
                http_client,
                allowed_hosts=allowed_hosts or ALLOWED_HOSTS,
                cancel_token=cancel_token,
            )

    def update_builtin_modpack(
        self,
        instance_id: str,
        *,
        allowed_hosts: tuple[str, ...] | None = None,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> Instance:
        cancel_request = cancel_token or CancelToken()
        registry = self.paths.instance_dir(instance_id)
        # Loading first lets an interrupted transaction recover before acquiring its lock.
        load_instance(self.paths, instance_id)
        with sync_lock(registry):
            instance = load_instance(self.paths, instance_id)
            game_dir = self.instance_game_dir(instance)
            recover_sync_update(registry, game_dir)
            pack_path = self.latest_builtin_pack(
                load_forgotten_worlds_pack(), allowed_hosts, cancel_request
            )
            plan = self._plan_modrinth_pack(pack_path, allowed_hosts)
            target = self.describe_content_target(instance_id)
            expected_version = (
                f"{plan.loader_kind}-loader-{plan.loader_version}-{plan.game_version}"
            )
            if (target.game_version, target.loader_kind) != (
                plan.game_version,
                plan.loader_kind,
            ) or instance.version_id != expected_version:
                raise ContentError("Modpack mới không khớp Minecraft và loader của bản chơi này.")
            desired = bundle_receipt(
                pack_path, read_index(pack_path, allowed_hosts=allowed_hosts or ALLOWED_HOSTS)
            )
            original = load_builtin_receipt(registry)
            if original is None:
                installed = legacy_pack_version(game_dir)
                if not installed:
                    raise ContentError("Bản chơi này không phải modpack Forgotten Worlds.")
                original = desired if installed == desired.version_id else legacy_receipt()
            tasks: list[DownloadTask] = []
            with (
                tempfile.TemporaryDirectory(
                    prefix="builtin-update-", dir=self.paths.instances_dir
                ) as temporary,
                self.make_http_client() as http_client,
            ):
                stage = Path(temporary)
                plan.apply_overrides(stage)
                previous = {
                    bundled_file.file_identity: path
                    for path, bundled_file in original.files.items()
                }
                for task in plan.tasks(stage):
                    relative = task.destination.relative_to(stage).as_posix()
                    bundled_file = desired.files[relative]
                    variant = existing_variant(game_dir, relative)
                    old_path = previous.get(bundled_file.file_identity)
                    if variant and matches(safe_sync_target(game_dir, variant), bundled_file):
                        continue
                    if old_path and not existing_variant(game_dir, old_path):
                        continue
                    tasks.append(task)
                report = download_all(
                    http_client,
                    tasks,
                    workers=8,
                    on_progress=on_progress,
                    cancel_token=cancel_request,
                )
                if not report.ok:
                    raise NetworkError("Chưa tải đủ bản cập nhật; dữ liệu cũ được giữ nguyên.")
                cancel_request.raise_if_cancelled()
                changes = plan_builtin_update(game_dir, stage, original, desired)
                touched = frozenset(changes.copies) | changes.removals
                with sync_transaction(registry, game_dir, touched):
                    for relative in sorted(changes.removals):
                        cancel_request.raise_if_cancelled()
                        safe_sync_target(game_dir, relative).unlink()
                    for relative, source in changes.copies.items():
                        cancel_request.raise_if_cancelled()
                        replace_sync_bytes(stage / source, safe_sync_target(game_dir, relative))
                    cancel_request.raise_if_cancelled()
                    save_builtin_receipt(registry, changes.receipt)
                    sync_directory(game_dir)
            return instance
