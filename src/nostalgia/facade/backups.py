"""Façade dữ liệu bản chơi: sao lưu, khôi phục và thùng rác."""

from __future__ import annotations

from pathlib import Path

from nostalgia.facade.context import LauncherContext
from nostalgia.instance.backups import (
    InstanceBackup,
    create_instance_backup,
    list_instance_backups,
    restore_instance_backup,
)
from nostalgia.instance.model import Instance
from nostalgia.instance.trash import (
    TrashedInstance,
    list_trashed_instances,
    restore_trashed_instance,
    trash_instance,
)


class BackupOperations(LauncherContext):
    __slots__ = ()

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
