"""Tải Nightly chính thức; kiểm chữ ký độc lập trước khi giải nén mã thực thi."""

from __future__ import annotations

import base64
import shutil
import tempfile
from pathlib import Path

from nostalgia.errors import IntegrityError, UnsupportedPlatformError
from nostalgia.horizon.archive import extract_horizon_bundle
from nostalgia.horizon.capability import load_build
from nostalgia.horizon.model import HorizonBuild, resolve_build_dir
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import ProgressFn, ignore_progress
from nostalgia.storage.files import atomic_write_json, ensure_dir
from nostalgia.storage.paths import DataPaths
from nostalgia.storage.sync_lock import sync_lock
from nostalgia.storage.windows_path import extended_windows_path
from nostalgia.system.platform_info import Platform
from nostalgia.update.download import download_bundle
from nostalgia.update.release import ReleaseAsset, parse_sha256sums

RELEASE_URL = "https://github.com/horizon-rust/horizon/releases/download/nightly"
RELEASE_KEY = "MU4oiIQcCxkZvbwSjjXs7SySCuM6ywRQ3nGaJYZG0gw="
PLATFORM_ASSETS = {
    ("linux", "x64"): "horizon-linux-x86_64.tar.gz",
    ("windows", "x64"): "horizon-windows-x64.zip",
    ("windows", "arm64"): "horizon-windows-arm64.zip",
    ("osx", "x64"): "horizon-macos-x64.zip",
    ("osx", "arm64"): "horizon-macos-arm64.zip",
}


def verify_release_signature(checksums: bytes, signature: bytes) -> None:
    """Khoá được ghim trong mã, không lấy cùng nguồn với gói vừa tải."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(RELEASE_KEY))
        public_key.verify(
            base64.b64decode(signature.strip(), validate=True),
            b"horizon release nightly\n" + checksums,
        )
    except (InvalidSignature, ValueError) as exc:
        raise IntegrityError("Invalid Horizon release signature; nothing was installed") from exc


def sync_horizon_build(
    http_client: HttpClient,
    paths: DataPaths,
    platform: Platform,
    *,
    on_progress: ProgressFn = ignore_progress,
    cancel_token: CancelToken | None = None,
) -> HorizonBuild:
    """Chỉ gọi khi người dùng tạo bản Horizon, không tự thay build của bản chơi đã có."""
    asset_name = PLATFORM_ASSETS.get((platform.os_name, platform.os_arch))
    if asset_name is None:
        raise UnsupportedPlatformError("Horizon has no official build for this platform")
    checksums = http_client.fetch_bytes(f"{RELEASE_URL}/SHA256SUMS", max_bytes=64 * 1024)
    signature = http_client.fetch_bytes(f"{RELEASE_URL}/SHA256SUMS.sig", max_bytes=1024)
    verify_release_signature(checksums, signature)
    build_id = parse_sha256sums(checksums.decode("utf-8")).get(asset_name, "")
    build_dir = resolve_build_dir(paths, build_id)
    if extended_windows_path(build_dir).is_dir():
        return load_build(paths, build_id, platform)
    ensure_dir(extended_windows_path(build_dir.parent))
    with sync_lock(extended_windows_path(build_dir.parent)):
        if extended_windows_path(build_dir).is_dir():
            return load_build(paths, build_id, platform)
        archive_path = download_bundle(
            http_client,
            ReleaseAsset(asset_name, f"{RELEASE_URL}/{asset_name}", 0),
            build_id,
            extended_windows_path(paths.data_dir / "horizon" / "downloads"),
            on_progress=on_progress,
            cancel_token=cancel_token,
        )
        with tempfile.TemporaryDirectory(
            prefix="stage-", dir=extended_windows_path(build_dir.parent)
        ) as temporary:
            staging_dir = Path(temporary)
            extracted = extract_horizon_bundle(archive_path, staging_dir, cancel_token)
            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            # Chỉ công bố cả thư mục khi đã giải nén xong; thế giới nằm bên ngoài vùng này.
            extracted.rename(extended_windows_path(build_dir))
        try:
            build = load_build(paths, build_id, platform)
        except BaseException:
            # Chỉ dọn build vừa tạo bởi giao dịch này, không đụng cache cũ hoặc thế giới.
            shutil.rmtree(extended_windows_path(build_dir))
            raise
        atomic_write_json(
            extended_windows_path(build_dir.parent / "receipt.json"),
            {
                "source": RELEASE_URL,
                "sha256": build_id,
                "minecraft": build.game_version,
            },
        )
        return build
