"""Chơi: dựng lệnh từ bản chơi + tài khoản rồi khởi động tiến trình game."""

from __future__ import annotations

from pathlib import Path

from nostalgia.account.model import ELY, Account, to_player_profile
from nostalgia.errors import InstanceError
from nostalgia.facade.accounts import AccountOperations
from nostalgia.install.assets import load_installed_asset_index
from nostalgia.instance.store import load_instance
from nostalgia.launch.authlib import (
    authlib_jvm_arguments,
    ensure_authlib_injector,
    fetch_api_metadata,
)
from nostalgia.launch.command import LaunchOptions, build_launch_command
from nostalgia.launch.game_process import GameProcess, OutputFn, ignore_output, start_game
from nostalgia.launch.runner import resolve_installed_java_binary
from nostalgia.launch.tuning import DEFAULT_MAX_HEAP_MEGABYTES, JvmTuning
from nostalgia.operations.cancellation import CancelToken
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.version.meta import VersionMeta


class PlayOperations(AccountOperations):
    __slots__ = ()

    def launch_instance(
        self,
        instance_id: str,
        player_name: str,
        *,
        client_id: str = "",
        on_output: OutputFn = ignore_output,
        cancel_token: CancelToken | None = None,
    ) -> GameProcess:
        """Khởi động một bản chơi và trả về tiến trình đang chạy.

        `client_id` chỉ cần khi tài khoản là Microsoft và vé đã tới lúc làm mới.
        """
        instance = load_instance(self.paths, instance_id)
        account = self._require_account(player_name, client_id, cancel_token)
        version_meta = VersionRepository(self.paths).load_version_meta(instance.version_id)
        java_binary = resolve_installed_java_binary(version_meta, self.platform, self.paths)
        if java_binary is None:
            message = f"chưa cài bản Java cho {instance.version_id}"
            raise InstanceError(message)

        tuning = JvmTuning(
            max_heap_megabytes=instance.max_heap_megabytes or DEFAULT_MAX_HEAP_MEGABYTES,
            extra_arguments=self._authlib_arguments(account),
        )
        command = build_launch_command(
            version_meta,
            self.platform,
            self.paths,
            to_player_profile(account),
            java_binary,
            LaunchOptions(
                game_dir=self.paths.instance_dir(instance.instance_id),
                window_width=instance.window_width,
                window_height=instance.window_height,
            ),
            tuning=tuning,
            virtual_assets_dir=self._virtual_assets_dir(version_meta),
        )
        return start_game(command, on_output=on_output)

    def _authlib_arguments(self, account: Account) -> tuple[str, ...]:
        """Tài khoản Ely.by: game hỏi skin/phiên qua Ely thay vì Mojang → tiêm authlib-injector."""
        if account.account_kind != ELY:
            return ()
        with self.make_http_client() as http_client:
            jar_path = ensure_authlib_injector(
                http_client, self.paths.data_dir / "authlib-injector", endpoints=self.auth_endpoints
            )
            metadata = fetch_api_metadata(http_client, self.auth_endpoints.ely_authlib_root_url)
        return authlib_jvm_arguments(jar_path, self.auth_endpoints.ely_authlib_root_url, metadata)

    def _virtual_assets_dir(self, version_meta: VersionMeta) -> Path | None:
        """Đời ≤1.7 đọc asset theo TÊN nên `--assetsDir` phải trỏ vào cây tên."""
        asset_index = load_installed_asset_index(version_meta, self.paths)
        if asset_index is None or not asset_index.is_virtual or not version_meta.assets_id:
            return None
        return self.paths.virtual_assets_dir(version_meta.assets_id)
