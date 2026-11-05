"""Chọn cache tương thích; cache mới mang SHA-256 trong đường dẫn để kiểm cả khi mất mạng."""

from __future__ import annotations

import re
from pathlib import Path

from nostalgia.nos_client.artifact import verify_mod_artifact
from nostalgia.nos_client.release import (
    MOD_JAR_PREFIX,
    resolve_artifact_game_version,
    resolve_mod_version,
    resolve_mod_version_key,
)


def find_cached_mod(
    cache: Path, game_version: str, *, loader_version: str = "", rejected: Path | None = None
) -> Path | None:
    jars = list((cache / game_version).glob(f"*/{MOD_JAR_PREFIX}*.jar"))
    # Cache launcher cũ chưa có thư mục game/hash. Chỉ nhận sau khi kiểm ZIP và metadata.
    jars.extend(cache.glob(f"{MOD_JAR_PREFIX}*.jar"))
    candidates = [
        path
        for path in jars
        if path != rejected and resolve_artifact_game_version(path.name) == game_version
    ]
    for path in sorted(
        candidates, key=lambda value: resolve_mod_version_key(value.name), reverse=True
    ):
        digest = None
        if path.parent != cache:
            if not re.fullmatch(r"[0-9a-f]{64}", path.parent.name):
                continue
            digest = path.parent.name
        if verify_mod_artifact(
            path,
            game_version,
            sha256=digest,
            mod_version=resolve_mod_version(path.name),
            loader_version=loader_version,
        ):
            return path
    return None
