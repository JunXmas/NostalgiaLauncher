"""Cài/gỡ Nos qua giao dịch thư mục mod sẵn có, có khóa, sao lưu và khôi phục sau gián đoạn."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from nostalgia.modrepair.transaction import lock_mods
from nostalgia.nos_client.artifact import load_nos_version, verify_mod_artifact
from nostalgia.nos_client.release import (
    MOD_JAR_PREFIX,
    resolve_artifact_game_version,
    resolve_mod_version_key,
)
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.directory_swap import (
    commit_directory,
    recover_directory,
    stage_directory,
    tree_fingerprint,
)

HISTORY_DIRECTORY = ".nostalgia-nos-updates"


def list_nos_jars(mods_dir: Path) -> tuple[Path, ...]:
    jars = []
    for path in sorted(mods_dir.glob("*.jar")):
        canonical_name = (
            MOD_JAR_PREFIX + path.name.removeprefix("nosclient-")
            if path.name.startswith("nosclient-")
            else path.name
        )
        if resolve_artifact_game_version(canonical_name) is not None or load_nos_version(path):
            jars.append(path)
    return tuple(jars)


def find_installed_mod(
    game_dir: Path, game_version: str, *, loader_version: str = ""
) -> Path | None:
    valid = [
        path
        for path in list_nos_jars(game_dir / "mods")
        if verify_mod_artifact(path, game_version, loader_version=loader_version)
    ]

    def version_key(path: Path) -> tuple[int, ...]:
        try:
            return resolve_mod_version_key(f"{MOD_JAR_PREFIX}{load_nos_version(path)}.jar")
        except ValueError:
            return ()

    return max(valid, key=version_key, default=None)


def inject_mod(
    cached_jar: Path, game_dir: Path, *, cancel_token: CancelToken | None = None
) -> Path:
    target = game_dir / "mods" / cached_jar.name
    _replace_mod(game_dir, cached_jar, cancel_token=cancel_token)
    return target


def remove_mod(game_dir: Path) -> None:
    _replace_mod(game_dir, None)


def recover_nos_install(game_dir: Path) -> None:
    with lock_mods(game_dir):
        recover_directory(game_dir / "mods", game_dir / HISTORY_DIRECTORY)


def _replace_mod(
    game_dir: Path, cached_jar: Path | None, *, cancel_token: CancelToken | None = None
) -> None:
    with lock_mods(game_dir):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        mods = game_dir / "mods"
        history = game_dir / HISTORY_DIRECTORY
        recover_directory(mods, history)
        previous = list_nos_jars(mods)
        if cached_jar is None and not previous:
            return
        if cached_jar is not None and len(previous) == 1 and previous[0].name == cached_jar.name:
            with previous[0].open("rb") as installed, cached_jar.open("rb") as cached:
                if (
                    hashlib.file_digest(installed, "sha256").digest()
                    == hashlib.file_digest(cached, "sha256").digest()
                ):
                    return
        original = tree_fingerprint(mods)
        with tempfile.TemporaryDirectory(prefix=".nos-stage-", dir=game_dir) as temporary:
            staged = Path(temporary) / "mods"
            stage_directory(mods, staged)
            if cached_jar is not None:
                # Luôn ghi inode mới: file cũ trong stage có thể hardlink với bản đang dùng.
                descriptor, name = tempfile.mkstemp(prefix=".nos-client-", dir=staged)
                with os.fdopen(descriptor, "wb") as destination, cached_jar.open("rb") as source:
                    shutil.copyfileobj(source, destination)
                    destination.flush()
                    os.fsync(destination.fileno())
                Path(name).replace(staged / cached_jar.name)
            for old in previous:
                if cached_jar is None or old.name != cached_jar.name:
                    (staged / old.name).unlink()
            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            commit_directory(mods, staged, history, original)
