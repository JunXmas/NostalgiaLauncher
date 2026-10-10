"""Trước khi khởi chạy, bộ mod trên đĩa phải khớp với bộ đã chia sẻ trong room."""

import hashlib
from pathlib import Path

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.sync_manifest import SYNC_DIRECTORIES
from nostalgia.multiplayer.sync_model import SyncSnapshot
from nostalgia.operations.cancellation import CancelToken


def verify_snapshot_source(
    game_dir: Path, snapshot: SyncSnapshot, excluded_mods: frozenset[str], cancel_token: CancelToken
) -> None:
    excluded_mods = frozenset(value.removesuffix(".disabled") for value in excluded_mods)
    expected = {sync_file.relative_path: sync_file for sync_file in snapshot.manifest.files}
    actual = set()
    if game_dir.is_symlink():
        raise MultiplayerError("Bản chơi đã thay đổi. Hãy tạo lại room trước khi chạy game.")

    def unreadable(error: OSError) -> None:
        raise error

    for directory in SYNC_DIRECTORIES:
        folder = game_dir / directory
        if folder.is_symlink():
            raise MultiplayerError("Bản chơi có liên kết thư mục; không khởi chạy room.")
        if not folder.exists():
            continue
        for parent, directories, names in folder.walk(follow_symlinks=False, on_error=unreadable):
            cancel_token.raise_if_cancelled()
            if any((parent / child).is_symlink() for child in directories):
                raise MultiplayerError("Bản chơi có liên kết thư mục; không khởi chạy room.")
            directories[:] = [child for child in directories if not child.startswith(".")]
            for file_name in names:
                if file_name.startswith("."):
                    continue
                path = parent / file_name
                relative_path = path.relative_to(game_dir).as_posix()
                if directory == "mods" and relative_path.removesuffix(".disabled") in excluded_mods:
                    continue
                sync_file = expected.get(relative_path)
                if (
                    not sync_file
                    or path.is_symlink()
                    or not path.is_file()
                    or path.stat().st_size != sync_file.size
                ):
                    raise MultiplayerError(
                        "Bản chơi đã thay đổi. Hãy tạo lại room trước khi chạy game."
                    )
                digest = hashlib.sha256()
                with path.open("rb") as reader:
                    while chunk := reader.read(256 * 1024):
                        cancel_token.raise_if_cancelled()
                        digest.update(chunk)
                if digest.hexdigest() != sync_file.sha256:
                    raise MultiplayerError(
                        "Bản chơi đã thay đổi. Hãy tạo lại room trước khi chạy game."
                    )
                actual.add(relative_path)
    if actual != set(expected):
        raise MultiplayerError("Bản chơi đã thay đổi. Hãy tạo lại room trước khi chạy game.")
