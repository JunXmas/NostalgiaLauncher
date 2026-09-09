"""Forge và NeoForge: liệt kê bản từ maven-metadata.xml, cài bằng installer chính thức.

Installer chạy headless (`--installClient <data_dir>`) ghi ra version JSON kiểu `inheritsFrom`
và tải thư viện vào đúng cây `libraries/` của ta — sau đó `install_version(version_id)` kiểm
lại và bù phần thiếu, rồi launch đi đường quen. Không tự viết lại bộ `processors` của Forge:
đó là hàng nghìn dòng dễ sai, và installer chính thức đã làm đúng.

Forge đời cũ (installer chưa có `--installClient`, ≤ 1.12.1) đi đường `forge_legacy.py`: không
cần chạy Java, chỉ ghi JSON và jar universal từ chính installer.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from nostalgia.errors import VersionError
from nostalgia.model.download import DownloadTask
from nostalgia.model.json_value import as_mapping, as_string
from nostalgia.modloader.forge_legacy import install_legacy_forge, is_legacy_installer
from nostalgia.modloader.model import LoaderVersion
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import fetch_json
from nostalgia.operations.cancellation import CancelToken
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS, Endpoints
from nostalgia.storage.files import atomic_write_json, ensure_dir

MAX_METADATA_BYTES = 4 * 1024 * 1024
INSTALLER_TIMEOUT_SECONDS = 600
INSTALLER_ATTEMPTS = 3
VERSION_TAG = re.compile(r"<version>([^<]+)</version>")


def fetch_forge_versions(
    http_client: HttpClient,
    game_version: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> tuple[LoaderVersion, ...]:
    """Bản Forge cho `game_version`, mới nhất đứng đầu; `stable` = bản recommended. CHẠM MẠNG.

    Forge đời cũ nhét nhánh phụ vào tên (`1.7.10-10.13.4.1614-1.7.10`), nên lấy nguyên tên
    thư mục maven làm khoá thay vì tự ghép `{game}-{forge}`.
    """
    names = _maven_versions(
        http_client, f"{endpoints.forge_maven}/maven-metadata.xml", cancel_token
    )
    promotions = as_mapping(
        as_mapping(
            fetch_json(
                http_client,
                endpoints.forge_promotions,
                what="promotions Forge",
                max_bytes=MAX_METADATA_BYTES,
                cancel_token=cancel_token,
            )
        ).get("promos")
    )
    recommended = as_string(promotions.get(f"{game_version}-recommended")) or ""
    prefix = f"{game_version}-"
    # maven-metadata.xml KHÔNG xếp theo thời gian với các bản cũ (1.7.10 có hàng trăm build
    # xen kẽ), nên sắp theo số hiệu build. Bản recommended khớp cả tên có hậu tố
    # (`1.7.10-10.13.4.1614-1.7.10`) lẫn không (`1.20.1-47.4.10`).
    found = sorted(
        (
            LoaderVersion(
                loader_version=name,
                stable=bool(recommended)
                and (
                    name == f"{prefix}{recommended}" or name.startswith(f"{prefix}{recommended}-")
                ),
                installer_url=f"{endpoints.forge_maven}/{name}/forge-{name}-installer.jar",
            )
            for name in names
            if name.startswith(prefix)
        ),
        key=lambda candidate: forge_build_number(candidate.loader_version, prefix),
        reverse=True,
    )
    if not found:
        message = f"Forge không có bản nào cho Minecraft {game_version!r}"
        raise VersionError(message)
    return tuple(found)


def fetch_neoforge_versions(
    http_client: HttpClient,
    game_version: str,
    *,
    endpoints: Endpoints = DEFAULT_ENDPOINTS,
    cancel_token: CancelToken | None = None,
) -> tuple[LoaderVersion, ...]:
    """Bản NeoForge cho `game_version`, mới nhất đứng đầu; `stable` = không phải beta. CHẠM MẠNG.

    NeoForge bỏ tiền tố `1.`: Minecraft 1.21.1 -> `21.1.x`, 1.21 -> `21.0.x`.
    """
    prefix = neoforge_prefix(game_version)
    names = _maven_versions(
        http_client, f"{endpoints.neoforge_maven}/maven-metadata.xml", cancel_token
    )
    found = [
        LoaderVersion(
            loader_version=name,
            stable="-beta" not in name,
            installer_url=f"{endpoints.neoforge_maven}/{name}/neoforge-{name}-installer.jar",
        )
        for name in reversed(names)
        if name.startswith(prefix)
    ]
    if not found:
        message = f"NeoForge không có bản nào cho Minecraft {game_version!r} (1.20.2 trở lên)"
        raise VersionError(message)
    return tuple(found)


def forge_build_number(name: str, prefix: str) -> tuple[int, ...]:
    """`1.7.10-10.13.4.1614-1.7.10` -> (10, 13, 4, 1614): phần sau tiền tố game, trước hậu tố."""
    build = name[len(prefix) :].split("-", 1)[0]
    return tuple(int(part) if part.isdigit() else 0 for part in build.split("."))


def neoforge_prefix(game_version: str) -> str:
    parts = game_version.split(".")
    minor = parts[1] if len(parts) > 1 else game_version
    patch = parts[2] if len(parts) > 2 else "0"
    return f"{minor}.{patch}."


def run_installer(
    http_client: HttpClient,
    data_dir: Path,
    versions_dir: Path,
    libraries_dir: Path,
    java_binary: Path,
    installer_url: str,
    *,
    cancel_token: CancelToken | None = None,
) -> str:
    """Tải installer, chạy `--installClient`, trả về `version_id` mới sinh. CHẠM MẠNG, chạy Java.

    Installer chính thức tự tải thư viện và chỉ cần một cú rớt mạng là bỏ cuộc; chạy lại thì
    nó bỏ qua phần đã đúng, nên thử tối đa `INSTALLER_ATTEMPTS` lần.
    """
    import subprocess  # nhập trễ: đường nhanh của CLI không cần nó

    installer_dir = ensure_dir(data_dir / "installers")
    jar_path = installer_dir / installer_url.rsplit("/", 1)[-1]
    download_one(
        http_client,
        DownloadTask(url=installer_url, destination=jar_path),
        cancel_token=cancel_token,
    )
    if is_legacy_installer(jar_path):
        try:
            return install_legacy_forge(jar_path, versions_dir, libraries_dir)
        finally:
            jar_path.unlink(missing_ok=True)

    profiles_path = data_dir / "launcher_profiles.json"
    if not profiles_path.is_file():
        # Installer đòi file này như một launcher Mojang; nội dung không quan trọng.
        atomic_write_json(profiles_path, {"profiles": {}, "settings": {}, "version": 3})
    before = _version_dirs(versions_dir)
    last_output = ""
    try:
        for attempt in range(INSTALLER_ATTEMPTS):
            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            try:
                completed = subprocess.run(
                    [str(java_binary), "-jar", str(jar_path), "--installClient", str(data_dir)],
                    capture_output=True,
                    text=True,
                    timeout=INSTALLER_TIMEOUT_SECONDS,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                last_output = f"installer không xong sau {INSTALLER_TIMEOUT_SECONDS} giây"
                continue
            fresh = sorted(_version_dirs(versions_dir) - before)
            if fresh and completed.returncode == 0:
                return fresh[-1]
            if "Successfully installed" in completed.stdout:
                return fresh[-1] if fresh else _reinstalled_version_id(versions_dir, jar_path)
            last_output = completed.stdout[-600:] + completed.stderr[-300:]
            time.sleep(2.0 * (attempt + 1))
    finally:
        jar_path.unlink(missing_ok=True)
    message = f"installer thất bại sau {INSTALLER_ATTEMPTS} lần:\n{last_output}"
    raise VersionError(message)


def _reinstalled_version_id(versions_dir: Path, jar_path: Path) -> str:
    """Cài lại bản đã có: không có thư mục mới, suy id từ tên installer."""
    stem = jar_path.name.removesuffix("-installer.jar")
    for candidate in sorted(_version_dirs(versions_dir)):
        if stem.split("-", 1)[-1] in candidate:
            return candidate
    message = f"installer báo xong nhưng không thấy thư mục version nào cho {stem}"
    raise VersionError(message)


def _version_dirs(versions_dir: Path) -> set[str]:
    if not versions_dir.is_dir():
        return set()
    return {child.name for child in versions_dir.iterdir() if child.is_dir()}


def _maven_versions(
    http_client: HttpClient, url: str, cancel_token: CancelToken | None
) -> list[str]:
    xml = http_client.fetch_bytes(url, max_bytes=MAX_METADATA_BYTES, cancel_token=cancel_token)
    return VERSION_TAG.findall(xml.decode("utf-8", errors="replace"))
