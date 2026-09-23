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
    INSTALL_KIND_APPIMAGE,
    INSTALL_KIND_FROZEN,
    INSTALL_KIND_READONLY,
    SwapPlan,
    blocked_install_reason,
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
from nostalgia.update.packages import (
    appimage_path,
    install_system_package,
    relaunch,
    replace_appimage,
)
from nostalgia.update.release import (
    LauncherRelease,
    ReleaseAsset,
    choose_bundle,
    choose_package,
    fetch_latest_release,
    is_newer,
)

# Kiểu cài tự lên bản mới được, mỗi kiểu một đường: tráo thư mục, thay file .AppImage, hoặc
# nhờ trình quản lý gói cài đè. Kiểu không có tên ở đây thì chỉ mở trang tải.
SELF_UPDATING_KINDS = (INSTALL_KIND_FROZEN, INSTALL_KIND_APPIMAGE, INSTALL_KIND_READONLY)


@dataclass(frozen=True, slots=True)
class StagedUpdate:
    """Bản mới đã tải và kiểm băm, chờ áp.

    `bundle_dir` là thư mục đã bung của gói `.zip` onedir; `package_path` là file gói hệ thống
    (`.AppImage`/`.deb`/`.rpm`) chưa bung. Đúng một trong hai có giá trị, tuỳ kiểu cài.
    """

    launcher_version: str
    bundle_dir: Path | None = None
    package_path: Path | None = None


class UpdateOperations(LauncherContext):
    __slots__ = ()

    def launcher_install_kind(self) -> str:
        """`frozen` (gói PyInstaller, tự áp được) hay `source` (chạy từ mã nguồn)."""
        return detect_install_kind()

    def launcher_update_asset(self, release: LauncherRelease) -> ReleaseAsset | None:
        """Gói phải tải cho kiểu cài của máy này: `.zip` onedir để tráo, hay `.AppImage`/
        `.deb`/`.rpm` để hệ thống cài hộ. Không có gói đúng thì None."""
        install_kind = self.launcher_install_kind()
        package = choose_package(release, install_kind, self.platform.os_arch)
        if package is not None:
            return package
        return choose_bundle(release, self.platform.os_name, self.platform.os_arch)

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
        if self.launcher_update_asset(release) is None:
            return None
        return release

    def download_launcher_update(
        self,
        release: LauncherRelease,
        *,
        on_progress: ProgressFn | None = None,
        cancel_token: CancelToken | None = None,
    ) -> StagedUpdate:
        """CHẠM MẠNG. Tải gói đúng KIỂU CÀI của máy này, đối chiếu SHA256SUMS.

        Gói `.zip` onedir thì bung vào `updates/<phiên bản>/` để tráo; gói hệ thống
        (`.AppImage`/`.deb`/`.rpm`) giữ nguyên file, để `apply_launcher_update` giao lại cho
        hệ thống. Cả hai đường đều PHẢI qua SHA256SUMS — đây là mã sắp chạy trên máy người dùng.
        """
        release_asset = self.launcher_update_asset(release)
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
        if not release_asset.name.endswith(".zip"):
            return StagedUpdate(release.launcher_version, package_path=bundle_path)
        bundle_dir = unpack_bundle(bundle_path, self.paths.updates_dir / release.launcher_version)
        return StagedUpdate(release.launcher_version, bundle_dir=_bundle_root(bundle_dir))

    def apply_launcher_update(self, staged: StagedUpdate) -> Path | None:
        """Áp bản đã tải theo đúng kiểu cài; người gọi PHẢI thoát launcher ngay sau đó.

        Ba đường: gói onedir ghi được thì chạy script tráo thư mục (trả về đường dẫn script);
        AppImage thì ghi đè chính file `.AppImage` rồi mở lại; `.deb`/`.rpm` thì nhờ trình
        quản lý gói cài đè qua `pkexec` rồi mở lại. Kiểu khác (mã nguồn, macOS `.app`) ném
        `UpdateError` với câu giải thích — người gọi lùi về mở trang tải."""
        install_kind = self.launcher_install_kind()
        if install_kind == INSTALL_KIND_FROZEN:
            return self._swap_bundle(staged)
        if install_kind == INSTALL_KIND_APPIMAGE:
            self._replace_appimage(staged)
            return None
        if install_kind == INSTALL_KIND_READONLY:
            self._install_package(staged)
            return None
        raise UpdateError(blocked_install_reason(install_kind))

    def _swap_bundle(self, staged: StagedUpdate) -> Path:
        if staged.bundle_dir is None:
            raise UpdateError("bản đã tải không phải gói .zip để tráo thư mục")
        install_dir = current_install_dir()
        executable = install_dir / Path(sys.executable).name
        plan = SwapPlan(install_dir, staged.bundle_dir, executable, os.getpid())
        script_path = write_swap_script(plan, self.paths.updates_dir)
        launch_swap_script(script_path)
        return script_path

    def _replace_appimage(self, staged: StagedUpdate) -> None:
        target = appimage_path()
        if staged.package_path is None or target is None:
            raise UpdateError("không tìm thấy file .AppImage đang chạy để thay")
        replace_appimage(staged.package_path, target)
        relaunch(target)

    def _install_package(self, staged: StagedUpdate) -> None:
        if staged.package_path is None:
            raise UpdateError("bản đã tải không phải gói .deb/.rpm để cài đè")
        install_system_package(staged.package_path)
        relaunch(current_install_dir() / Path(sys.executable).name)


def _bundle_root(bundle_dir: Path) -> Path:
    """Zip thường bọc mọi thứ trong một thư mục con duy nhất; lấy đúng thư mục chứa launcher."""
    children = [child for child in bundle_dir.iterdir() if not child.name.startswith(".")]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return bundle_dir
