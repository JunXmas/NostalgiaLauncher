"""Thao tác Nos Client: bật/tắt, cấu hình HUD, tải và inject mod jar.

Facade này kế thừa `InstanceOperations` — mọi thao tác cần biết bản chơi nào, ở đâu — và
được ghép vào `Launcher` qua `api.py`.
"""

from __future__ import annotations

import logging
from dataclasses import replace

from nostalgia.errors import NetworkError
from nostalgia.facade.context import LauncherContext
from nostalgia.instance.model import Instance
from nostalgia.instance.store import game_dir_of, save_instance
from nostalgia.modcheck.predicate import resolve_version
from nostalgia.nos_client.artifact import load_nos_version
from nostalgia.nos_client.compatibility import resolve_nos_game_version, resolve_nos_loader_version
from nostalgia.nos_client.config import (
    NosClientConfig,
    load_nos_client_config,
    save_nos_client_config,
)
from nostalgia.nos_client.installation import (
    find_installed_mod,
    inject_mod,
    recover_nos_install,
    remove_mod,
)
from nostalgia.nos_client.manager import sync_mod_cached
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress

logger = logging.getLogger(__name__)


class NosClientOperations(LauncherContext):
    __slots__ = ()

    def nos_client_supported(self, instance: Instance) -> bool:
        """Dùng chung quy tắc tương thích cho công tắc UI và bước chuẩn bị trước khi chơi."""
        return resolve_nos_game_version(instance.version_id) is not None

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

    def prepare_nos_client(
        self,
        instance: Instance,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> None:
        """Chuẩn bị Nos Client trước khi launch: tải mod nếu cần, inject vào mods/.

        Chỉ gọi khi `instance.nos_client_enabled` là True.
        """
        if not instance.nos_client_enabled:
            return
        game_version = resolve_nos_game_version(instance.version_id)
        if game_version is None:
            logger.warning("Nos Client does not support %s", instance.version_id)
            return
        game_dir = game_dir_of(self.paths, instance)
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        recover_nos_install(game_dir)
        on_progress(Progress("Kiểm tra cập nhật Nos Client", 0, 1))
        loader_version = resolve_nos_loader_version(instance.version_id)
        with self.make_http_client() as http_client:
            cached = sync_mod_cached(
                http_client,
                self.paths,
                game_version,
                loader_version=loader_version,
                cancel_token=cancel_token,
            )
        installed = find_installed_mod(game_dir, game_version, loader_version=loader_version)
        if installed is not None and (
            cached is None
            or (
                (resolve_version(load_nos_version(installed)) or (0, 0, 0))
                > (resolve_version(load_nos_version(cached)) or (0, 0, 0))
            )
        ):
            cached = installed
        if cached is None:
            raise NetworkError(
                "Không có bản Nos Client tương thích đã xác minh. "
                "Kiểm tra kết nối mạng và phiên bản Fabric rồi thử lại."
            )
        inject_mod(cached, game_dir, cancel_token=cancel_token)
        on_progress(Progress("Nos Client đã sẵn sàng", 1, 1))

    def cleanup_nos_client(self, instance: Instance) -> None:
        """Xóa mod jar khi tắt Nos Client."""
        remove_mod(game_dir_of(self.paths, instance))
