"""Tìm bản Nos ổn định tương thích, xác minh trước khi commit cache, giữ bản cũ khi lỗi mạng."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path

from nostalgia.errors import IntegrityError, NetworkError
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.nos_client.artifact import verify_mod_artifact
from nostalgia.nos_client.cache import find_cached_mod
from nostalgia.nos_client.compatibility import SUPPORTED_GAME_VERSIONS
from nostalgia.nos_client.release import (
    fetch_compatible_release,
    fetch_release_sha256,
    resolve_mod_version,
)
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import ensure_dir, sync_directory
from nostalgia.storage.paths import DataPaths
from nostalgia.update.download import sha256_of_file

logger = logging.getLogger(__name__)


def sync_mod_cached(
    http_client: HttpClient,
    paths: DataPaths,
    game_version: str,
    *,
    loader_version: str = "",
    cancel_token: CancelToken | None = None,
) -> Path | None:
    if game_version not in SUPPORTED_GAME_VERSIONS:
        return None
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    cache = paths.data_dir / "nos-client"
    release = fetch_compatible_release(http_client, game_version, cancel_token=cancel_token)
    rejected = None
    if release is not None:
        try:
            digest = fetch_release_sha256(http_client, release, cancel_token=cancel_token)
            if digest is None:
                raise IntegrityError(f"Missing SHA-256 for Nos Client: {release.file_name}")
            cached_jar = cache / game_version / digest / release.file_name
            if verify_mod_artifact(
                cached_jar,
                game_version,
                sha256=digest,
                size=release.size,
                mod_version=resolve_mod_version(release.file_name),
                loader_version=loader_version,
            ):
                return cached_jar
            legacy = cache / release.file_name
            legacy_valid = (
                legacy.is_file()
                and not legacy.is_symlink()
                and legacy.stat().st_size == release.size
                and sha256_of_file(legacy) == digest
            )
            if legacy.exists() and not legacy_valid:
                rejected = legacy
                legacy.unlink()
            ensure_dir(cached_jar.parent)
            with tempfile.TemporaryDirectory(prefix=".download-", dir=cached_jar.parent) as staging:
                staged_jar = Path(staging) / release.file_name
                if legacy_valid:
                    shutil.copyfile(legacy, staged_jar)
                else:
                    download_one(
                        http_client,
                        DownloadTask(release.download_url, staged_jar, size=release.size),
                        cancel_token=cancel_token,
                    )
                if not verify_mod_artifact(
                    staged_jar,
                    game_version,
                    sha256=digest,
                    size=release.size,
                    mod_version=resolve_mod_version(release.file_name),
                    loader_version=loader_version,
                ):
                    raise IntegrityError(f"Invalid Nos Client artifact: {release.file_name}")
                if cancel_token is not None:
                    cancel_token.raise_if_cancelled()
                staged_jar.replace(cached_jar)
                sync_directory(cached_jar.parent)
            return cached_jar
        except (NetworkError, IntegrityError, OSError, ValueError):
            logger.warning("Could not update Nos Client for Minecraft %s", game_version)
    return find_cached_mod(cache, game_version, loader_version=loader_version, rejected=rejected)
