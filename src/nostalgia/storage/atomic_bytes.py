"""Atomic byte writes for properties and configuration, using the same durability as JSON."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from nostalgia.storage.files import ensure_dir, sync_directory


def atomic_write(path: Path, payload: bytes) -> None:
    ensure_dir(path.parent)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + "-")
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
        sync_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)
