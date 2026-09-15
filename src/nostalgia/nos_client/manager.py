"""Quản lý mod jar của Nos Client: tải, inject, và xóa phiên bản cũ.

Mod jar được tải từ GitHub Releases của repo mod, lưu vào cache chung của launcher,
rồi copy vào `mods/` của từng instance khi cần.
"""

from __future__ import annotations


import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from nostalgia.errors import NetworkError
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.storage.files import ensure_dir
from nostalgia.storage.paths import DataPaths

logger = logging.getLogger(__name__)

# Tổ chức mod mà launcher quản lý: GitHub owner/repo cho API Releases.
GITHUB_REPO_OWNER = "JunXmas"
GITHUB_REPO_NAME = "NostalgiaLauncher-legacy"
GITHUB_API_BASE = "https://api.github.com"
MOD_JAR_PREFIX = "nos-client-"
MOD_CACHE_DIR_NAME = "nos-client"


@dataclass(frozen=True, slots=True)
class ModRelease:
    """Một bản phát hành của mod trên GitHub."""

    tag: str
    release_version: str
    download_url: str
    file_name: str
    size: int | None = None


def _fetch_latest_release(http_client: HttpClient) -> ModRelease | None:
    """Lấy bản phát hành mới nhất từ GitHub Releases API.

    Trả về None nếu không có release nào hoặc release không có file .jar.
    """
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"
    try:
        response = http_client.get_json(
            url, headers={"Accept": "application/vnd.github+json"}
        )
    except NetworkError:
        logger.warning("không lấy được thông tin release từ GitHub")
        return None

    if not isinstance(response, dict):
        return None

    tag = response.get("tag_name", "")
    release_artifacts = response.get("assets", [])
    if not isinstance(release_artifacts, list):
        return None

    for artifact in release_artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_name = artifact.get("name", "")
        if isinstance(artifact_name, str) and artifact_name.endswith(".jar") and artifact_name.startswith(MOD_JAR_PREFIX):
            download_url = artifact.get("browser_download_url", "")
            artifact_size = artifact.get("size")
            mod_version = tag.lstrip("v")
            return ModRelease(
                tag=tag,
                release_version=mod_version,
                download_url=download_url,
                file_name=artifact_name,
                size=artifact_size if isinstance(artifact_size, int) else None,
            )
    return None


def _cache_dir(paths: DataPaths) -> Path:
    """Thư mục cache cho mod jar: `<data_dir>/nos-client/`."""
    return paths.data_dir / MOD_CACHE_DIR_NAME


def ensure_mod_cached(
    http_client: HttpClient, paths: DataPaths
) -> Path | None:
    """Đảm bảo mod jar có trong cache. Tải về nếu chưa có hoặc có phiên bản mới.

    Trả về đường dẫn tới file jar trong cache, hoặc None nếu không tải được.
    """
    release = _fetch_latest_release(http_client)
    if release is None:
        # Không có release mới; dùng file đã cache nếu có.
        return _find_cached_jar(paths)

    cache = ensure_dir(_cache_dir(paths))
    cached_jar = cache / release.file_name

    if cached_jar.is_file():
        return cached_jar

    # Xóa phiên bản cũ trước khi tải mới.
    _clean_old_jars(cache)

    task = DownloadTask(
        url=release.download_url,
        destination=cached_jar,
        size=release.size,
    )
    try:
        download_one(http_client, task)
    except Exception:
        logger.warning("không tải được mod jar: %s", release.download_url)
        return _find_cached_jar(paths)
    return cached_jar


def _find_cached_jar(paths: DataPaths) -> Path | None:
    """Tìm file jar đã cache (bất kỳ phiên bản nào)."""
    cache = _cache_dir(paths)
    if not cache.is_dir():
        return None
    jars = sorted(cache.glob(f"{MOD_JAR_PREFIX}*.jar"), reverse=True)
    return jars[0] if jars else None


def _clean_old_jars(cache_dir: Path) -> None:
    """Xóa mọi file jar cũ trong thư mục cache."""
    for old_jar in cache_dir.glob(f"{MOD_JAR_PREFIX}*.jar"):
        try:
            old_jar.unlink()
        except OSError:
            logger.warning("không xóa được jar cũ: %s", old_jar)


def inject_mod(cached_jar: Path, game_dir: Path) -> Path:
    """Copy mod jar vào `mods/` của instance. Xóa phiên bản cũ nếu có.

    Trả về đường dẫn của file jar trong mods/.
    """
    mods_dir = ensure_dir(game_dir / "mods")

    # Xóa phiên bản cũ.
    for old in mods_dir.glob(f"{MOD_JAR_PREFIX}*.jar"):
        try:
            old.unlink()
        except OSError:
            logger.warning("không xóa được mod cũ: %s", old)

    target = mods_dir / cached_jar.name
    shutil.copy2(cached_jar, target)
    return target


def remove_mod(game_dir: Path) -> None:
    """Xóa mod jar khỏi `mods/` của instance."""
    mods_dir = game_dir / "mods"
    if not mods_dir.is_dir():
        return
    for jar in mods_dir.glob(f"{MOD_JAR_PREFIX}*.jar"):
        try:
            jar.unlink()
        except OSError:
            logger.warning("không xóa được mod: %s", jar)
