"""Thao tác Nos Client: bật/tắt, cấu hình HUD, tải và inject mod jar.

Facade này kế thừa `InstanceOperations` — mọi thao tác cần biết bản chơi nào, ở đâu — và
được ghép vào `Launcher` qua `api.py`.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from nostalgia.facade.context import LauncherContext
from nostalgia.instance.model import Instance
from nostalgia.instance.store import game_dir_of, save_instance
from nostalgia.nos_client.config import (
    NosClientConfig,
    load_nos_client_config,
    save_nos_client_config,
)
from nostalgia.nos_client.manager import ensure_mod_cached, inject_mod, remove_mod

logger = logging.getLogger(__name__)


class NosClientOperations(LauncherContext):
    __slots__ = ()

    def nos_client_config(self, instance: Instance) -> NosClientConfig:
        """Đọc cấu hình HUD của Nos Client cho một bản chơi."""
        return load_nos_client_config(game_dir_of(self.paths, instance))

    def set_nos_client_config(self, instance: Instance, config: NosClientConfig) -> None:
        """Ghi cấu hình HUD trước khi launch."""
        save_nos_client_config(game_dir_of(self.paths, instance), config)

    def toggle_nos_client(self, instance: Instance, enabled: bool) -> Instance:
        """Bật hoặc tắt Nos Client cho một bản chơi. Trả về instance đã cập nhật."""
        updated = replace(instance, nos_client_enabled=enabled)
        save_instance(self.paths, updated)
        return updated

    def prepare_nos_client(self, instance: Instance) -> None:
        """Chuẩn bị Nos Client trước khi launch: tải mod nếu cần, inject vào mods/.

        Chỉ gọi khi `instance.nos_client_enabled` là True.
        """
        if not instance.nos_client_enabled:
            return
        game_dir = game_dir_of(self.paths, instance)
        with self.make_http_client() as http_client:
            cached = ensure_mod_cached(http_client, self.paths)
        if cached is not None:
            inject_mod(cached, game_dir)
        else:
            logger.warning("không có mod jar — bỏ qua inject cho %s", instance.instance_id)

    def cleanup_nos_client(self, instance: Instance) -> None:
        """Xóa mod jar khi tắt Nos Client."""
        remove_mod(game_dir_of(self.paths, instance))
