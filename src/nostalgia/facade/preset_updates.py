"""Update the bundled server pack in its existing instance, with rollback and backups."""

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
from nostalgia.errors import ContentError, NetworkError
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


@dataclass(frozen=True, slots=True)
class BuiltinPackStatus:
    installed_version: str
    available_version: str

    @property
    def update_available(self) -> bool:
        return self.installed_version != self.available_version


class PresetUpdateOperations(ModpackOperations):
    __slots__ = ()

    def builtin_pack_status(self, instance: Instance) -> BuiltinPackStatus | None:
        game_dir = self.instance_game_dir(instance)
        receipt = load_builtin_receipt(self.paths.instance_dir(instance.instance_id))
        version = receipt.version if receipt is not None else legacy_pack_version(game_dir)
        if not version:
            return None
        pack = load_forgotten_worlds_pack()
        latest = bundle_version(pack)
        return BuiltinPackStatus(version, latest)

    def update_builtin_modpack(
        self,
        instance_id: str,
        *,
        allowed_hosts: tuple[str, ...] | None = None,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> Instance:
        token = cancel_token or CancelToken()
        registry = self.paths.instance_dir(instance_id)
        # Loading first lets an interrupted transaction recover before acquiring its lock.
        load_instance(self.paths, instance_id)
        with sync_lock(registry):
            instance = load_instance(self.paths, instance_id)
            game_dir = self.instance_game_dir(instance)
            recover_sync_update(registry, game_dir)
            pack = load_forgotten_worlds_pack()
            plan = self._plan_modrinth_pack(pack, allowed_hosts)
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
                pack, read_index(pack, allowed_hosts=allowed_hosts or ALLOWED_HOSTS)
            )
            original = load_builtin_receipt(registry)
            if original is None:
                installed = legacy_pack_version(game_dir)
                if not installed:
                    raise ContentError("Bản chơi này không phải modpack Forgotten Worlds.")
                original = desired if installed == desired.version else legacy_receipt()
            tasks: list[DownloadTask] = []
            with (
                tempfile.TemporaryDirectory(
                    prefix="builtin-update-", dir=self.paths.instances_dir
                ) as temporary,
                self.make_http_client() as http_client,
            ):
                stage = Path(temporary)
                plan.apply_overrides(stage)
                previous = {entry.identity: path for path, entry in original.files.items()}
                for task in plan.tasks(stage):
                    relative = task.destination.relative_to(stage).as_posix()
                    entry = desired.files[relative]
                    variant = existing_variant(game_dir, relative)
                    old_path = previous.get(entry.identity)
                    if variant and matches(safe_sync_target(game_dir, variant), entry):
                        continue
                    if old_path and not existing_variant(game_dir, old_path):
                        continue
                    tasks.append(task)
                report = download_all(
                    http_client, tasks, workers=8, on_progress=on_progress, cancel_token=token
                )
                if not report.ok:
                    raise NetworkError("Chưa tải đủ bản cập nhật; dữ liệu cũ được giữ nguyên.")
                token.raise_if_cancelled()
                changes = plan_builtin_update(game_dir, stage, original, desired)
                touched = frozenset(changes.copies) | changes.removals
                with sync_transaction(registry, game_dir, touched):
                    for relative in sorted(changes.removals):
                        token.raise_if_cancelled()
                        safe_sync_target(game_dir, relative).unlink()
                    for relative, source in changes.copies.items():
                        token.raise_if_cancelled()
                        replace_sync_bytes(stage / source, safe_sync_target(game_dir, relative))
                    token.raise_if_cancelled()
                    save_builtin_receipt(registry, changes.receipt)
                    sync_directory(game_dir)
            return instance
