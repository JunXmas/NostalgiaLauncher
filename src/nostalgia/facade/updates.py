"""Tự cập nhật launcher: kiểm bản mới, tải + kiểm băm, áp (khi chạy từ gói đóng sẵn)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from nostalgia import __version__
from nostalgia.errors import UpdateError
from nostalgia.facade.context import LauncherContext
from nostalgia.operations.cancellation import CancelToken
from nostalgia.update.apply import (
    INSTALL_KIND_FROZEN,
    SwapPlan,
    current_install_dir,
    detect_install_kind,
    launch_swap_script,
    write_swap_script,
)
from nostalgia.update.download import (
    ProgressFn,
    download_bundle,
    fetch_expected_sums,
    unpack_bundle,
)
from nostalgia.update.release import LauncherRelease, choose_bundle, fetch_latest_release, is_newer


@dataclass(frozen=True, slots=True)
class StagedUpdate:
    """Bản mới đã tải, kiểm băm và bung sẵn, chờ áp."""

    launcher_version: str
    bundle_dir: Path


class UpdateOperations(LauncherContext):
    __slots__ = ()

    def launcher_install_kind(self) -> str:
        """`frozen` (gói PyInstaller, tự áp được) hay `source` (chạy từ mã nguồn)."""
        return detect_install_kind()

    def check_launcher_update(self) -> LauncherRelease | None:
        """CHẠM MẠNG. Bản mới hơn `__version__` có gói cho máy này; không thì None."""
        with self.make_http_client() as http_client:
            release = fetch_latest_release(http_client, endpoints=self.endpoints)
        if (
            release is None
            or release.prerelease
            or not is_newer(release.launcher_version, __version__)
        ):
            return None
        if choose_bundle(release, self.platform.os_name, self.platform.os_arch) is None:
            return None
        return release

    def download_launcher_update(
        self,
        release: LauncherRelease,
        *,
        on_progress: ProgressFn | None = None,
        cancel_token: CancelToken | None = None,
    ) -> StagedUpdate:
        """CHẠM MẠNG. Tải gói đúng hệ, đối chiếu SHA256SUMS, bung vào `updates/<phiên bản>/`."""
        release_asset = choose_bundle(release, self.platform.os_name, self.platform.os_arch)
        if release_asset is None:
            raise UpdateError(
                f"bản {release.launcher_version} không có gói cho {self.platform.os_name}"
            )
        with self.make_http_client() as http_client:
            sums = fetch_expected_sums(http_client, release)
            expected = sums.get(release_asset.name)
            if expected is None:
                raise UpdateError(f"SHA256SUMS không có dòng cho {release_asset.name} — không cài")
            bundle_path = download_bundle(
                http_client,
                release_asset,
                expected,
                self.paths.updates_dir,
                on_progress=on_progress,
                cancel_token=cancel_token,
            )
        bundle_dir = unpack_bundle(bundle_path, self.paths.updates_dir / release.launcher_version)
        return StagedUpdate(release.launcher_version, _bundle_root(bundle_dir))

    def apply_launcher_update(self, staged: StagedUpdate) -> Path:
        """Viết và chạy script tráo thư mục; người gọi PHẢI thoát launcher ngay sau đó.
        Chỉ cho gói đóng sẵn — chạy từ mã nguồn thì ném `UpdateError`."""
        if self.launcher_install_kind() != INSTALL_KIND_FROZEN:
            raise UpdateError("đang chạy từ mã nguồn: cập nhật bằng `git pull` và `uv sync`")
        install_dir = current_install_dir()
        executable = install_dir / Path(sys.executable).name
        plan = SwapPlan(install_dir, staged.bundle_dir, executable, os.getpid())
        script_path = write_swap_script(plan, self.paths.updates_dir)
        launch_swap_script(script_path)
        return script_path


def _bundle_root(bundle_dir: Path) -> Path:
    """Zip thường bọc mọi thứ trong một thư mục con duy nhất; lấy đúng thư mục chứa launcher."""
    children = [child for child in bundle_dir.iterdir() if not child.name.startswith(".")]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return bundle_dir
