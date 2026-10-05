"""Nối mọi mảnh lại: cài đủ một phiên bản, rồi khởi động nó.

Module này **không tự biết gì cả** — nó chỉ gọi các mảnh đã có theo đúng thứ tự và đúng một
lần. Mọi luật (file nào cần, tải ở đâu, lệnh gồm gì) đều nằm ở các module bên dưới; ở đây
chỉ còn trình tự.

Thứ tự có ý nghĩa: chỉ mục asset phải tải xong mới biết cần những object nào; natives phải
bung xong trước khi dựng lệnh vì lệnh trỏ vào thư mục đó; và bản Java tải cuối vì nó nặng
nhất, để một lỗi rẻ tiền không bắt người dùng chờ 51 MB rồi mới báo.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import NetworkError
from nostalgia.install.assets import (
    build_name_tree,
    load_installed_asset_index,
    plan_asset_index_task,
    plan_asset_tasks,
)
from nostalgia.install.client import plan_client_task
from nostalgia.install.library import plan_libraries
from nostalgia.install.natives import extract_natives
from nostalgia.java.component import (
    resolve_java_binary,
    resolve_java_component,
    resolve_runtime_os_keys,
)
from nostalgia.java.mojang_jre import ensure_java_runtime
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import DEFAULT_WORKERS, DownloadReport, download_all
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.version.meta import VersionMeta


@dataclass(frozen=True, slots=True)
class InstallReport:
    """Kết quả một lượt cài đủ."""

    version_meta: VersionMeta
    java_binary: Path
    downloaded: int
    skipped: int
    bytes_written: int


def install_version(
    version_id: str,
    http_client: HttpClient,
    paths: DataPaths,
    platform: Platform,
    *,
    game_dir: Path | None = None,
    workers: int = DEFAULT_WORKERS,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
) -> InstallReport:
    """Cài đủ mọi thứ để chạy được một phiên bản. Gọi lại lần hai gần như không làm gì.

    `endpoints` là tham số để test trỏ sang máy chủ cục bộ — cùng lý do đã ghi ở
    `repo/manifest.py`: sửa hằng mức module trong test là để lại trạng thái cho mọi test sau.
    """
    repository = VersionRepository(paths, http_client, manifest_url=endpoints.version_manifest)
    version_meta = repository.sync_version_meta(version_id, cancel_token=cancel_token)

    library_plan = plan_libraries(version_meta, platform, paths)
    first_wave: list[DownloadTask] = list(library_plan.downloads)
    client_task = plan_client_task(version_meta, paths)
    if client_task is not None:
        first_wave.append(client_task)
    if version_meta.asset_index is not None:
        first_wave.append(plan_asset_index_task(version_meta.asset_index, paths))
    downloaded = _download(http_client, first_wave, workers, on_progress, cancel_token, "cài đặt")

    asset_index = load_installed_asset_index(version_meta, paths)
    if asset_index is not None:
        downloaded = _add(
            downloaded,
            _download(
                http_client,
                plan_asset_tasks(asset_index, paths, base_url=endpoints.asset_objects),
                workers,
                on_progress,
                cancel_token,
                "asset",
            ),
        )

    extract_natives(
        library_plan.natives_to_extract,
        paths.natives_dir(version_meta.version_id),
        cancel_token=cancel_token,
    )
    if asset_index is not None and version_meta.assets_id:
        # `build_name_tree` tự quyết định có cần dựng hay không. Kiểm lại ở đây là để hai nơi
        # cùng biết một luật, và một ngày nào đó hai nơi đó hiểu khác nhau.
        build_name_tree(
            asset_index, version_meta.assets_id, paths, game_dir or paths.data_dir / "game"
        )

    installed_runtime = ensure_java_runtime(
        http_client,
        paths,
        version_meta,
        platform,
        workers=workers,
        on_progress=on_progress,
        cancel_token=cancel_token,
        catalog_url=endpoints.java_catalog,
    )
    return InstallReport(
        version_meta=version_meta,
        java_binary=installed_runtime.java_binary,
        downloaded=downloaded.downloaded,
        skipped=downloaded.skipped,
        bytes_written=downloaded.bytes_written,
    )


def resolve_installed_java_binary(
    version_meta: VersionMeta, platform: Platform, paths: DataPaths
) -> Path | None:
    """Tìm bản Java ĐÃ CÀI trên đĩa, không chạm mạng.

    Có mặt để `play` chạy được khi không có mạng: `ensure_java_runtime` luôn phải tải hai
    tầng manifest, mà một bản đã cài đủ thì không cần hỏi Mojang thêm gì nữa.
    """
    java_component = resolve_java_component(version_meta)
    for runtime_os_key in resolve_runtime_os_keys(platform):
        runtime_root = paths.java_runtime_dir(java_component, runtime_os_key)
        java_binary = resolve_java_binary(runtime_root, platform.os_name)
        if java_binary.is_file():
            return java_binary
    return None


def _download(
    http_client: HttpClient,
    tasks: list[DownloadTask],
    workers: int,
    on_progress: ProgressFn,
    cancel_token: CancelToken | None,
    what: str,
) -> DownloadReport:
    report = download_all(
        http_client, tasks, workers=workers, on_progress=on_progress, cancel_token=cancel_token
    )
    if not report.ok:
        first = report.failures[0]
        message = (
            f"{what}: thiếu {len(report.failures)}/{len(tasks)} file; "
            f"lỗi đầu tiên: {first.task.url}: {first.reason}"
        )
        raise NetworkError(message)
    return report


def _add(first: DownloadReport, second: DownloadReport) -> DownloadReport:
    return DownloadReport(
        downloaded=first.downloaded + second.downloaded,
        skipped=first.skipped + second.skipped,
        bytes_written=first.bytes_written + second.bytes_written,
        failures=(),
    )
