"""Bản chơi: đăng ký, lưu, gỡ, và thống kê chơi (giờ chơi, số lần chạy, thế giới, mod)."""

from __future__ import annotations

from pathlib import Path

from nostalgia.content.installed import list_installed
from nostalgia.facade.context import LauncherContext
from nostalgia.instance.model import Instance
from nostalgia.instance.stats import (
    InstanceStats,
    PlayStats,
    count_worlds,
    load_play_stats,
    record_play_session,
)
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

    def describe_instance_stats(self, instance_id: str) -> InstanceStats:
        """Chỉ đọc đĩa: số liệu đã ghi + đếm thế giới trong `saves/` và mod trong `mods/`."""
        game_dir = self.paths.instance_dir(instance_id)
        return InstanceStats(
            play=load_play_stats(self.paths, instance_id),
            world_count=count_worlds(game_dir),
            mod_count=len(list_installed(game_dir, "mod")),
        )

    def record_play_session(
        self, instance_id: str, started_at: float, ended_at: float
    ) -> PlayStats:
        """Game vừa thoát: cộng phiên chơi vào số liệu của bản chơi đó."""
        return record_play_session(self.paths, instance_id, started_at, ended_at)
