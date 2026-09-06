"""Bản chơi: đăng ký, lưu, gỡ."""

from __future__ import annotations

from pathlib import Path

from nostalgia.facade.context import LauncherContext
from nostalgia.instance.model import Instance
from nostalgia.instance.store import (
    create_instance,
    list_instances,
    save_instance,
    unregister_instance,
)


class InstanceOperations(LauncherContext):
    __slots__ = ()

    def list_instances(self) -> tuple[Instance, ...]:
        return list_instances(self.paths)

    def create_instance(self, instance: Instance) -> Instance:
        return create_instance(self.paths, instance)

    def save_instance(self, instance: Instance) -> None:
        save_instance(self.paths, instance)

    def remove_instance(self, instance_id: str) -> Path:
        """Gỡ đăng ký và trả về thư mục chơi **vẫn còn nguyên** thế giới trong đó."""
        return unregister_instance(self.paths, instance_id)
