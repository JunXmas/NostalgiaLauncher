"""Bản chơi: đăng ký, lưu, gỡ, và thống kê chơi (giờ chơi, số lần chạy, thế giới, mod)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from nostalgia.content.installed import list_installed
from nostalgia.errors import ContentError
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
    check_game_dir_override,
    create_instance,
    game_dir_of,
    list_instances,
    load_instance,
    save_instance,
    unregister_instance,
)
from nostalgia.settings.store import load_settings


class InstanceOperations(LauncherContext):
    __slots__ = ()

    def list_instances(self) -> tuple[Instance, ...]:
        return list_instances(self.paths)

    def create_instance(self, instance: Instance) -> Instance:
        """Đăng ký bản chơi. Không chọn thư mục riêng mà CÀI ĐẶT có "thư mục lưu bản chơi" thì
        bản chơi vào `<thư mục đó>/<mã>` — cách đơn giản để dồn mọi bản chơi sang ổ còn chỗ."""
        override = instance.game_dir_override
        if not override:
            default_root = load_settings(self.paths.config_dir).default_game_dir_root
            if default_root:
                override = str(Path(default_root) / instance.instance_id)
        checked = replace(instance, game_dir_override=check_game_dir_override(self.paths, override))
        return create_instance(self.paths, checked)

    def require_instance_id_free(self, instance_id: str) -> None:
        """Rớt sớm — trước khi tải hàng trăm MB modpack — nếu mã bản chơi đã có."""
        if instance_id in {instance.instance_id for instance in list_instances(self.paths)}:
            message = f"đã có bản chơi {instance_id!r}"
            raise ContentError(message)

    def instance_game_dir(self, instance: Instance) -> Path:
        """Thư mục chơi thật (mods, saves): mặc định hay ổ riêng do người dùng chọn."""
        return game_dir_of(self.paths, instance)

    def check_game_dir(self, text: str) -> str:
        """Kiểm một đường dẫn người dùng gõ/chọn trước khi dùng làm thư mục chơi."""
        return check_game_dir_override(self.paths, text)

    def save_instance(self, instance: Instance) -> None:
        save_instance(self.paths, instance)

    def remove_instance(self, instance_id: str) -> Path:
        """Gỡ đăng ký và trả về thư mục chơi **vẫn còn nguyên** thế giới trong đó."""
        return unregister_instance(self.paths, instance_id)

    def describe_instance_stats(self, instance_id: str) -> InstanceStats:
        """Chỉ đọc đĩa: số liệu đã ghi + đếm thế giới trong `saves/` và mod trong `mods/`."""
        game_dir = game_dir_of(self.paths, load_instance(self.paths, instance_id))
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
