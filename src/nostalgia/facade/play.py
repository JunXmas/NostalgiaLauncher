"""Chơi: dựng lệnh từ bản chơi + tài khoản rồi khởi động tiến trình game."""

from __future__ import annotations

import logging
from pathlib import Path

from nostalgia.account.model import ELY, Account, to_player_profile
from nostalgia.errors import InstanceError, NetworkError
from nostalgia.facade.accounts import AccountOperations
from nostalgia.install.assets import load_installed_asset_index
from nostalgia.instance.store import game_dir_of, load_instance
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

logger = logging.getLogger(__name__)


class PlayOperations(AccountOperations):
    __slots__ = ()

    def launch_instance(
        self,
        instance_id: str,
        account_id: str,
        *,
        client_id: str = "",
        world_folder: str = "",
        server_address: str = "",
        on_output: OutputFn = ignore_output,
        cancel_token: CancelToken | None = None,
    ) -> GameProcess:
        """Khởi động một bản chơi và trả về tiến trình đang chạy.

        `client_id` chỉ cần khi tài khoản là Microsoft và vé đã tới lúc làm mới. `world_folder`
        (tên thư mục trong saves/) đưa game vào thẳng thế giới đó — chỉ tác dụng từ 1.20.
        """
        instance = load_instance(self.paths, instance_id)
        account = self._require_account(account_id, client_id, cancel_token)
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
                game_dir=game_dir_of(self.paths, instance),
                window_width=instance.window_width,
                window_height=instance.window_height,
                world_folder=world_folder,
                server_address=server_address,
            ),
            tuning=tuning,
            virtual_assets_dir=self._virtual_assets_dir(version_meta),
        )
        return start_game(command, on_output=on_output)

    def prefetch_skin_support(self) -> Path:
        """Tải sẵn authlib-injector — thứ làm skin Ely.by hiện trong game. CHẠM MẠNG.

        Gọi ngay sau khi thêm tài khoản Ely, chứ không đợi tới lúc bấm CHƠI: lúc vừa đăng nhập
        thì người dùng đang cầm mạng và đang chờ sẵn, còn lúc bấm CHƠI họ đang nôn nóng vào
        game và một lỗi mạng ở đó đọc ra "launcher hỏng".
        """
        with self.make_http_client() as http_client:
            return ensure_authlib_injector(
                http_client, self._authlib_dir, endpoints=self.auth_endpoints
            )

    def skin_support_ready(self) -> bool:
        """Đã có jar trên đĩa chưa. KHÔNG chạm mạng — chỉ để hiện trạng thái, không để quyết."""
        return any(self._authlib_dir.glob("authlib-injector-*.jar"))

    @property
    def _authlib_dir(self) -> Path:
        return self.paths.data_dir / "authlib-injector"

    def _authlib_arguments(self, account: Account) -> tuple[str, ...]:
        """Tài khoản Ely.by: game hỏi skin/phiên qua Ely thay vì Mojang → tiêm authlib-injector.

        MẠNG hỏng thì KHÔNG chặn: trả về `()` và game chạy bình thường, chỉ mất skin. Thiếu
        skin không đáng đánh đổi cả buổi chơi — và `ensure_authlib_injector` đã tự lùi về jar
        cũ trên đĩa, nên tới được đây nghĩa là chưa từng tải được lần nào.

        `IntegrityError` thì KHÔNG nuốt. Băm không khớp nghĩa là file tải về không phải thứ
        trang chủ công bố, và đây là mã sắp chạy trong JVM game — đó là tín hiệu bảo mật, phải
        nổi lên tới người dùng chứ không phải một dòng nhật ký rồi chơi tiếp như không có gì.
        """
        if account.account_kind != ELY:
            return ()
        try:
            jar_path = self.prefetch_skin_support()
        except NetworkError:
            logger.warning(
                "chưa tải được authlib-injector — skin Ely.by sẽ không hiện trong game",
                exc_info=True,
            )
            return ()
        with self.make_http_client() as http_client:
            metadata = fetch_api_metadata(http_client, self.auth_endpoints.ely_authlib_root_url)
        return authlib_jvm_arguments(jar_path, self.auth_endpoints.ely_authlib_root_url, metadata)

    def _virtual_assets_dir(self, version_meta: VersionMeta) -> Path | None:
        """Đời ≤1.7 đọc asset theo TÊN nên `--assetsDir` phải trỏ vào cây tên."""
        asset_index = load_installed_asset_index(version_meta, self.paths)
        if asset_index is None or not asset_index.is_virtual or not version_meta.assets_id:
            return None
        return self.paths.virtual_assets_dir(version_meta.assets_id)
