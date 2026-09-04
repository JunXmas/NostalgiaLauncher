"""Cài bản Java của Mojang: hai tầng manifest, tải, bung, rồi trả về đường dẫn `java`.

Không dùng Java sẵn có trên máy: mỗi phiên bản Minecraft chỉ được kiểm với đúng bản Mojang
chỉ định, và bản trên máy người chơi có thể là bất cứ đời nào. Tìm Java hệ thống là việc của
một module khác, dùng khi người chơi cố tình chọn.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import DataFileError, NetworkError, UnsupportedPlatformError
from nostalgia.java.component import (
    resolve_java_binary,
    resolve_java_component,
    resolve_runtime_os_keys,
)
from nostalgia.java.runtime_manifest import (
    RuntimeCatalog,
    RuntimeLayout,
    RuntimeRelease,
    parse_runtime_catalog,
    parse_runtime_layout,
)
from nostalgia.java.runtime_plan import RuntimePlan, plan_runtime
from nostalgia.java.unpack import (
    apply_executable_bits,
    create_directories,
    create_links,
    decode_compressed,
)
from nostalgia.net.download import DEFAULT_WORKERS, download_all
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import fetch_json
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.repo.endpoints import JAVA_RUNTIME_MANIFEST_URL
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform
from nostalgia.version.meta import VersionMeta


@dataclass(frozen=True, slots=True)
class InstalledRuntime:
    """Một bản Java đã cài xong và sẵn sàng chạy.

    Khác `JavaRuntimeRef` trong `version/meta.py`: cái kia là *khai báo* trong JSON phiên
    bản (chỉ có tên component và số major), cái này là *kết quả* — đã có file trên đĩa.
    """

    java_binary: Path
    java_component: str
    runtime_os_key: str
    version_name: str


def fetch_runtime_catalog(
    http_client: HttpClient, *, url: str = JAVA_RUNTIME_MANIFEST_URL
) -> RuntimeCatalog:
    """Tải danh mục bản Java. `url` là tham số để test trỏ sang máy chủ cục bộ."""
    runtime_catalog = parse_runtime_catalog(fetch_json(http_client, url, what="danh mục bản Java"))
    if not runtime_catalog.releases:
        message = "danh mục bản Java rỗng — máy chủ trả về thứ không dùng được"
        raise DataFileError(message)
    return runtime_catalog


def fetch_runtime_layout(http_client: HttpClient, release: RuntimeRelease) -> RuntimeLayout:
    """Tải manifest chi tiết của một bản: 391 mục cho `jre-legacy/linux`."""
    what = f"manifest bản Java {release.java_component}/{release.runtime_os_key}"
    layout = parse_runtime_layout(fetch_json(http_client, release.manifest.url, what=what))
    if not layout.files:
        message = f"{what} không có file nào"
        raise DataFileError(message)
    return layout


def select_runtime_release(
    runtime_catalog: RuntimeCatalog, version_meta: VersionMeta, platform: Platform
) -> RuntimeRelease:
    """Chọn bản Java cho phiên bản game này trên nền tảng này. THUẦN: không I/O."""
    java_component = resolve_java_component(version_meta)
    runtime_os_keys = resolve_runtime_os_keys(platform)
    if not runtime_os_keys:
        message = f"không có bản Java cho {platform.os_name}/{platform.os_arch}"
        raise UnsupportedPlatformError(message)
    release = runtime_catalog.find(java_component, runtime_os_keys)
    if release is None:
        message = (
            f"Mojang không phát hành {java_component} cho {'/'.join(runtime_os_keys)} "
            f"({platform.os_name}/{platform.os_arch})"
        )
        raise UnsupportedPlatformError(message)
    return release


def install_runtime(
    http_client: HttpClient,
    plan: RuntimePlan,
    *,
    workers: int = DEFAULT_WORKERS,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
) -> int:
    """Thi hành kế hoạch. Trả về tổng số byte đã ghi ra đĩa.

    Thứ tự bắt buộc: thư mục trước (manifest khai cả thư mục rỗng), rồi tải, rồi bung, rồi
    cờ thực thi, rồi liên kết — liên kết trỏ tới file nên file phải có mặt trước.
    """
    create_directories(plan.directories)
    report = download_all(
        http_client,
        list(plan.downloads),
        workers=workers,
        on_progress=on_progress,
        cancel_token=cancel_token,
    )
    if not report.ok:
        first = report.failures[0]
        message = (
            f"tải bản Java thiếu {len(report.failures)}/{len(plan.downloads)} file; "
            f"lỗi đầu tiên: {first.task.url}: {first.reason}"
        )
        raise NetworkError(message)

    written = report.bytes_written
    written += decode_compressed(
        plan.archives_to_decode, on_progress=on_progress, cancel_token=cancel_token
    )
    for stale_archive in plan.stale_archives:
        stale_archive.unlink(missing_ok=True)
    apply_executable_bits(plan.executables)
    create_links(plan.links)
    return written


def ensure_java_runtime(
    http_client: HttpClient,
    paths: DataPaths,
    version_meta: VersionMeta,
    platform: Platform,
    *,
    workers: int = DEFAULT_WORKERS,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
    catalog_url: str = JAVA_RUNTIME_MANIFEST_URL,
) -> InstalledRuntime:
    """Đảm bảo có bản Java đúng cho `version_meta`, rồi trả về đường dẫn `java`.

    Gọi lại lần hai gần như không làm gì: kế hoạch loại hết file đã đúng, nên chỉ còn hai
    request cho hai tầng manifest.
    """
    release = select_runtime_release(
        fetch_runtime_catalog(http_client, url=catalog_url), version_meta, platform
    )
    runtime_root = paths.java_runtime_dir(release.java_component, release.runtime_os_key)
    plan = plan_runtime(fetch_runtime_layout(http_client, release), runtime_root)
    install_runtime(
        http_client, plan, workers=workers, on_progress=on_progress, cancel_token=cancel_token
    )
    return InstalledRuntime(
        java_binary=resolve_java_binary(runtime_root, platform.os_name),
        java_component=release.java_component,
        runtime_os_key=release.runtime_os_key,
        version_name=release.version_name,
    )
