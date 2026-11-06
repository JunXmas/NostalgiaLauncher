"""Điều phối cài và chạy Horizon; tài nguyên native không lẫn với mod Java."""

from __future__ import annotations

from nostalgia.account.model import ELY, MICROSOFT, Account
from nostalgia.errors import InstanceError
from nostalgia.facade.context import LauncherContext
from nostalgia.horizon.capability import load_build
from nostalgia.horizon.command import build_horizon_command
from nostalgia.horizon.model import HorizonBuild
from nostalgia.horizon.preparation import sync_horizon_preparation
from nostalgia.horizon.process import start_horizon
from nostalgia.horizon.release import sync_horizon_build
from nostalgia.horizon.resource import check_resources, prepare_resources
from nostalgia.instance.model import Instance
from nostalgia.instance.store import game_dir_of
from nostalgia.launch.command import LaunchOptions
from nostalgia.launch.game_process import GameProcess, OutputFn
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.skin.textures import cached_skin, refresh_ely_skin, skin_cache_key
from nostalgia.storage.sync_lock import sync_lock


class HorizonOperations(LauncherContext):
    __slots__ = ()

    def install_horizon(
        self,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> HorizonBuild:
        """Tải bản chính thức đã kiểm chữ ký; chỉ dùng lúc tạo bản chơi mới."""
        with self.make_http_client() as http_client:
            return sync_horizon_build(
                http_client,
                self.paths,
                self.platform,
                on_progress=on_progress,
                cancel_token=cancel_token,
            )

    def prepare_horizon_instance(
        self,
        instance: Instance,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> None:
        build = load_build(self.paths, instance.horizon_build_id, self.platform)
        if build.version_id != instance.version_id:
            raise InstanceError("Horizon build and instance Minecraft versions differ")
        with sync_lock(build.build_dir.parent):
            if check_resources(build, cancel_token):
                return
            with self.make_http_client() as http_client:
                prepared = sync_horizon_preparation(
                    http_client,
                    self.paths,
                    build,
                    self.platform,
                    on_progress=on_progress,
                    cancel_token=cancel_token,
                    endpoints=self.endpoints,
                )
            prepare_resources(
                self.paths,
                build,
                prepared.java_binary,
                prepared.server_jar,
                input_paths=prepared.input_paths,
                on_progress=on_progress,
                cancel_token=cancel_token,
            )

    def start_horizon_instance(
        self,
        instance: Instance,
        account: Account,
        *,
        world_folder: str,
        server_address: str,
        on_output: OutputFn,
        cancel_token: CancelToken | None,
    ) -> GameProcess:
        build = load_build(self.paths, instance.horizon_build_id, self.platform)
        if build.version_id != instance.version_id or not check_resources(build, cancel_token):
            raise InstanceError("Prepare this Horizon instance before playing")
        cache_key = skin_cache_key(account.account_kind, account.player_name, account.player_uuid)
        player_skin = cached_skin(self.paths.skins_dir, cache_key, account.player_uuid)
        if account.account_kind == ELY:
            with self.make_http_client() as http_client:
                player_skin = refresh_ely_skin(
                    http_client,
                    self.paths.skins_dir,
                    account.player_name,
                    account.player_uuid,
                    endpoints=self.endpoints,
                )
        command = build_horizon_command(
            build,
            account,
            LaunchOptions(
                game_dir=game_dir_of(self.paths, instance),
                window_width=instance.window_width,
                window_height=instance.window_height,
                world_folder=world_folder,
                server_address=server_address,
            ),
            None if account.account_kind == MICROSOFT else player_skin,
        )
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        return start_horizon(command, on_output=on_output)
