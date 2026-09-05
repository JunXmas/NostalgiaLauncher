"""Cửa duy nhất mà giao diện được phép đi qua.

Kho tiền nhiệm không có lớp này, và hậu quả đo được: phần giao diện của nó import thẳng vào
**sáu module lõi** (`accounts`, `doctor`, `install`, `launch`, `paths`, `settings`). Mỗi lần
lõi đổi một chi tiết là giao diện gãy theo, và không ai dám sửa lõi nữa.

Luật của lớp này:

- **Nhận và trả dataclass**, không bao giờ trả `dict` thô hay đối tượng của thư viện chuẩn
  như `Popen`. `GameProcess` được trả ra, nhưng nó là bọc có chủ đích: người gọi chỉ thấy
  `pid`, `is_running`, `wait`, `stop`.
- **Dựng một lần, tiêm vào.** `Launcher` giữ `paths` và `platform`; không có đường dẫn mặc
  định ẩn nào nằm rải trong code. Nhờ vậy giao diện mở được hai profile song song, và test
  chạy song song được.
- **Không in ra màn hình.** Tiến độ đi qua `on_progress`, mã đăng nhập đi qua
  `on_device_code` — đúng như tầng `cli/` đang làm.

Giao diện chỉ được import: `nostalgia.api`, `nostalgia.errors`, `nostalgia.operations.progress`
và các dataclass mô hình. Có test gác ở `tests/test_api_boundary.py`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from nostalgia.account.microsoft import build_microsoft_account, needs_refresh, refresh_account
from nostalgia.account.model import Account, PlayerProfile, to_player_profile
from nostalgia.account.offline import build_offline_account
from nostalgia.account.store import (
    find_account,
    load_accounts,
    remove_account,
    save_accounts,
    upsert_account,
)
from nostalgia.auth.endpoints import DEFAULT_AUTH_ENDPOINTS, AuthEndpoints
from nostalgia.auth.microsoft import DeviceCodeFn, ignore_device_code, sign_in
from nostalgia.doctor import Diagnosis, diagnose
from nostalgia.errors import AccountError, InstanceError
from nostalgia.install.assets import load_installed_asset_index
from nostalgia.instance.model import Instance
from nostalgia.instance.store import (
    create_instance,
    list_instances,
    load_instance,
    save_instance,
    unregister_instance,
)
from nostalgia.launch.command import LaunchOptions, build_launch_command
from nostalgia.launch.game_process import GameProcess, OutputFn, ignore_output, start_game
from nostalgia.launch.runner import InstallReport, install_version, resolve_installed_java_binary
from nostalgia.launch.tuning import JvmTuning
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress, ProgressFn, ignore_progress
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints
from nostalgia.repo.manifest import ManifestEntry
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform, current_platform
from nostalgia.version.meta import VersionMeta


@dataclass(frozen=True, slots=True)
class Launcher:
    """Toàn bộ khả năng của lõi, gói sau một đối tượng dựng một lần rồi dùng lại."""

    paths: DataPaths
    platform: Platform = field(default_factory=current_platform)
    endpoints: Endpoints = DEFAULT_ENDPOINTS
    auth_endpoints: AuthEndpoints = DEFAULT_AUTH_ENDPOINTS
    # Điểm tiêm duy nhất cho phần mạng. Mặc định là bộ khách thật; test trỏ nó sang máy chủ
    # cục bộ, và một ngày nào đó giao diện muốn dùng proxy riêng cũng chỉ cần thay chỗ này.
    make_http_client: Callable[[], HttpClient] = HttpClient

    @classmethod
    def for_environment(cls) -> Launcher:
        """Dựng theo quy ước thư mục của hệ điều hành đang chạy."""
        platform = current_platform()
        return cls(paths=DataPaths.from_env(platform.os_name), platform=platform)

    @classmethod
    def for_data_dir(cls, data_dir: Path, config_dir: Path | None = None) -> Launcher:
        """Dựng ở một thư mục chỉ định.

        Có mặt để giao diện **không phải import `DataPaths`**: danh sách module mà giao diện
        được phép chạm càng ngắn thì ranh giới càng khó bị vượt qua vì tiện tay.
        """
        return cls(paths=DataPaths(data_dir=data_dir, config_dir=config_dir or data_dir))

    # ----- phiên bản -----

    def list_installed_versions(self) -> tuple[str, ...]:
        """Các bản đã có trên đĩa. Không chạm mạng."""
        return VersionRepository(self.paths).list_installed()

    def list_released_versions(self, *, limit: int = 50) -> tuple[ManifestEntry, ...]:
        """Danh mục bản chính thức của Mojang. CHẠM MẠNG."""
        with self.make_http_client() as http_client:
            manifest = VersionRepository(
                self.paths, http_client, manifest_url=self.endpoints.version_manifest
            ).fetch_manifest()
        return manifest.released()[: max(limit, 0)]

    def install_version(
        self,
        version_id: str,
        *,
        on_progress: ProgressFn = ignore_progress,
        cancel_token: CancelToken | None = None,
    ) -> InstallReport:
        """Tải đủ một phiên bản. CHẠM MẠNG. Gọi lại khi đã đủ thì gần như không làm gì."""
        with self.make_http_client() as http_client:
            return install_version(
                version_id,
                http_client,
                self.paths,
                self.platform,
                on_progress=on_progress,
                cancel_token=cancel_token,
                endpoints=self.endpoints,
            )

    def diagnose_version(self, version_id: str, *, verify_hashes: bool = False) -> Diagnosis:
        """Soi một bản cài. Không chạm mạng."""
        version_meta = VersionRepository(self.paths).load_version_meta(version_id)
        return diagnose(
            version_meta,
            self.platform,
            self.paths,
            asset_index=load_installed_asset_index(version_meta, self.paths),
            java_binary=resolve_installed_java_binary(version_meta, self.platform, self.paths),
            verify_hashes=verify_hashes,
        )

    # ----- bản chơi -----

    def list_instances(self) -> tuple[Instance, ...]:
        return list_instances(self.paths)

    def create_instance(self, instance: Instance) -> Instance:
        return create_instance(self.paths, instance)

    def save_instance(self, instance: Instance) -> None:
        save_instance(self.paths, instance)

    def remove_instance(self, instance_id: str) -> Path:
        """Gỡ đăng ký và trả về thư mục chơi **vẫn còn nguyên** thế giới trong đó."""
        return unregister_instance(self.paths, instance_id)

    # ----- tài khoản -----

    def list_accounts(self) -> tuple[Account, ...]:
        return load_accounts(self.paths.accounts_json)

    def add_offline_account(self, player_name: str) -> Account:
        return self._store(build_offline_account(player_name))

    def add_microsoft_account(
        self,
        client_id: str,
        *,
        on_device_code: DeviceCodeFn = ignore_device_code,
        cancel_token: CancelToken | None = None,
    ) -> Account:
        """Đăng nhập Microsoft. CHẠM MẠNG, và chờ người dùng nhập mã trên trang của họ."""
        with self.make_http_client() as http_client:
            login = sign_in(
                http_client,
                client_id,
                on_device_code,
                endpoints=self.auth_endpoints,
                cancel_token=cancel_token,
            )
        return self._store(build_microsoft_account(login, now=time.time()))

    def remove_account(self, player_name: str) -> None:
        accounts = self.list_accounts()
        if find_account(accounts, player_name) is None:
            message = f"không có tài khoản {player_name!r}"
            raise AccountError(message)
        save_accounts(self.paths.accounts_json, remove_account(accounts, player_name))

    # ----- chơi -----

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
            tuning=JvmTuning(max_heap_megabytes=instance.max_heap_megabytes)
            if instance.max_heap_megabytes
            else None,
            virtual_assets_dir=self._virtual_assets_dir(version_meta),
        )
        return start_game(command, on_output=on_output)

    def _require_account(
        self, player_name: str, client_id: str, cancel_token: CancelToken | None
    ) -> Account:
        account = find_account(self.list_accounts(), player_name)
        if account is None:
            message = f"không có tài khoản {player_name!r}"
            raise AccountError(message)
        if not needs_refresh(account, now=time.time()):
            return account
        with self.make_http_client() as http_client:
            refreshed = refresh_account(
                http_client,
                client_id,
                account,
                now=time.time(),
                endpoints=self.auth_endpoints,
                cancel_token=cancel_token,
            )
        return self._store(refreshed)

    def _virtual_assets_dir(self, version_meta: VersionMeta) -> Path | None:
        """Đời ≤1.7 đọc asset theo TÊN nên `--assetsDir` phải trỏ vào cây tên."""
        asset_index = load_installed_asset_index(version_meta, self.paths)
        if asset_index is None or not asset_index.is_virtual or not version_meta.assets_id:
            return None
        return self.paths.virtual_assets_dir(version_meta.assets_id)

    def _store(self, account: Account) -> Account:
        save_accounts(self.paths.accounts_json, upsert_account(self.list_accounts(), account))
        return account


__all__ = [
    "Account",
    "Diagnosis",
    "GameProcess",
    "InstallReport",
    "Instance",
    "Launcher",
    "PlayerProfile",
    "Progress",
]
