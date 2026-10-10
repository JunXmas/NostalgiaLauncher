"""Façade dữ liệu bản chơi: xuất modpack, xóa và khôi phục dữ liệu cũ."""

from __future__ import annotations

from pathlib import Path

from nostalgia.facade.context import LauncherContext
from nostalgia.facade.sync_loader import resolve_sync_loader
from nostalgia.instance.backups import (
    InstanceBackup,
    create_instance_backup,
    list_instance_backups,
    restore_instance_backup,
)
from nostalgia.instance.exporting import ExportEnvironment, ModpackExport, export_modpack
from nostalgia.instance.model import Instance
from nostalgia.instance.store import game_dir_of, load_instance
from nostalgia.instance.trash import (
    TrashedInstance,
    list_trashed_instances,
    remove_trashed_instance,
    restore_trashed_instance,
    trash_instance,
)
from nostalgia.modloader.model import detect_loader_kind
from nostalgia.repo.version_repo import VersionRepository


class BackupOperations(LauncherContext):
    __slots__ = ()

    def export_instance_modpack(
        self,
        instance_id: str,
        destination: Path,
        archive_format: str,
        *,
        include_worlds: bool = False,
        overwrite: bool = False,
    ) -> ModpackExport:
        """Đóng gói dữ liệu trên đĩa, không tải mạng và không xuất tài khoản launcher."""
        instance = load_instance(self.paths, instance_id)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        loader_kind = detect_loader_kind(instance.version_id)
        environment = ExportEnvironment(
            version_meta.jar_owner_id,
            loader_kind,
            resolve_sync_loader(
                loader_kind,
                version_meta.libraries,
                version_meta.jar_owner_id,
                game_arguments=version_meta.game_arguments,
            ),
        )
        return export_modpack(
            instance,
            game_dir_of(self.paths, instance),
            environment,
            destination,
            archive_format,
            include_worlds=include_worlds,
            overwrite=overwrite,
        )

    def list_instance_backups(self) -> tuple[InstanceBackup, ...]:
        return list_instance_backups(self.paths)

    def backup_instance(self, instance_id: str) -> InstanceBackup:
        return create_instance_backup(self.paths, instance_id)

    def restore_instance_backup(self, backup: Path, instance_id: str) -> Instance:
        return restore_instance_backup(self.paths, backup, instance_id)

    def list_trashed_instances(self) -> tuple[TrashedInstance, ...]:
        return list_trashed_instances(self.paths)

    def trash_instance(self, instance_id: str) -> str:
        return trash_instance(self.paths, instance_id)

    def restore_trashed_instance(self, trash_id: str) -> Instance:
        return restore_trashed_instance(self.paths, trash_id)

    def remove_trashed_instance(self, trash_id: str) -> None:
        remove_trashed_instance(self.paths, trash_id)
