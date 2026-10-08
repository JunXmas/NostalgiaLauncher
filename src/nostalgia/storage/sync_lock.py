"""Khóa liên tiến trình tự nhả khi ứng dụng thoát, không để khóa chết sau crash."""

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from nostalgia.errors import MultiplayerError


@contextmanager
def sync_lock(registry_dir: Path) -> Iterator[None]:
    path = registry_dir / ".nostalgia-sync.lock"
    if path.is_symlink() or registry_dir.is_symlink():
        raise MultiplayerError("Kho đồng bộ chứa symlink.")
    registry_dir.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.seek(0)
            stream.write(b"\0")
            stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            except OSError:
                raise MultiplayerError("Bản chơi đang được cập nhật ở cửa sổ khác.") from None
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        else:
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise MultiplayerError("Bản chơi đang được cập nhật ở cửa sổ khác.") from None
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
