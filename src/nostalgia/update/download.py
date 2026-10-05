"""Tải gói cập nhật về `updates_dir`: băm sha256 khi đang tải, đối chiếu SHA256SUMS, ghi
nguyên tử, rồi bung zip vào thư mục riêng theo phiên bản.

Gói này là MÃ SẼ CHẠY trên máy người dùng, nên luật chặt hơn release_asset game: không có SHA256SUMS
→ từ chối; sai băm → `IntegrityError` và xoá file dở; entry zip thoát thư mục → `UnsafePathError`.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

from nostalgia.errors import IntegrityError, UpdateError
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress
from nostalgia.storage.files import ensure_dir, resolve_within, set_executable, sync_directory
from nostalgia.update.release import (
    SUMS_ASSET_NAME,
    LauncherRelease,
    ReleaseAsset,
    parse_sha256sums,
)

MAX_SUMS_BYTES = 64 * 1024
MAX_BUNDLE_BYTES = 512 * 1024 * 1024
STAGE_DOWNLOAD = "tải bản mới"

type ProgressFn = Callable[[Progress], None]


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_expected_sums(http_client: HttpClient, release: LauncherRelease) -> dict[str, str]:
    """SHA256SUMS của bản phát hành. Không có là lỗi — không bao giờ cài gói không kiểm được."""
    sums_asset = release.asset_named(SUMS_ASSET_NAME)
    if sums_asset is None:
        raise UpdateError(f"bản {release.launcher_version} không kèm {SUMS_ASSET_NAME} — không cài")
    text = http_client.fetch_bytes(sums_asset.url, max_bytes=MAX_SUMS_BYTES).decode(
        "utf-8", errors="replace"
    )
    sums = parse_sha256sums(text)
    if not sums:
        raise UpdateError(
            f"{SUMS_ASSET_NAME} của bản {release.launcher_version} rỗng hoặc sai định dạng"
        )
    return sums


def download_bundle(
    http_client: HttpClient,
    release_asset: ReleaseAsset,
    expected_sha256: str,
    updates_dir: Path,
    *,
    on_progress: ProgressFn | None = None,
    cancel_token: CancelToken | None = None,
) -> Path:
    """Tải `release_asset` về `updates_dir/<tên>`; đã có file đúng băm thì dùng lại."""
    ensure_dir(updates_dir)
    destination = updates_dir / release_asset.name
    if destination.is_file() and sha256_of_file(destination) == expected_sha256:
        return destination

    digest = hashlib.sha256()
    received = 0
    handle_number, part_name = tempfile.mkstemp(
        prefix=f"{release_asset.name}.", suffix=".part", dir=updates_dir
    )
    part_path = Path(part_name)
    try:
        with os.fdopen(handle_number, "wb") as part:

            def write(chunk: bytes) -> None:
                nonlocal received
                part.write(chunk)
                digest.update(chunk)
                received += len(chunk)
                if on_progress is not None:
                    on_progress(Progress(STAGE_DOWNLOAD, received, release_asset.size))

            http_client.stream(
                release_asset.url,
                write,
                expected_size=release_asset.size or None,
                max_bytes=MAX_BUNDLE_BYTES,
                cancel_token=cancel_token,
            )
            part.flush()
            os.fsync(part.fileno())
        if digest.hexdigest() != expected_sha256:
            raise IntegrityError(f"{release_asset.name} tải về không khớp sha256 — không cài")
        part_path.replace(destination)
    except BaseException:
        part_path.unlink(missing_ok=True)
        raise
    sync_directory(updates_dir)
    return destination


def unpack_bundle(bundle_path: Path, target_dir: Path) -> Path:
    """Bung zip vào `target_dir` (xoá bản bung cũ nếu có). Mỗi entry đi qua `resolve_within`;
    file thực thi (bit x trong zip) được giữ quyền chạy."""
    if target_dir.exists():
        _remove_tree(target_dir)
    ensure_dir(target_dir)
    with zipfile.ZipFile(bundle_path) as archive:
        for info in archive.infolist():
            destination = resolve_within(target_dir, info.filename)
            if info.is_dir():
                ensure_dir(destination)
                continue
            ensure_dir(destination.parent)
            with archive.open(info) as source, destination.open("wb") as sink:
                for chunk in iter(lambda: source.read(1 << 20), b""):
                    sink.write(chunk)
            if (info.external_attr >> 16) & 0o111:
                set_executable(destination)
    return target_dir


def _remove_tree(directory: Path) -> None:
    for child in sorted(directory.rglob("*"), key=lambda found: len(found.parts), reverse=True):
        if child.is_dir() and not child.is_symlink():
            child.rmdir()
        else:
            child.unlink()
    directory.rmdir()
