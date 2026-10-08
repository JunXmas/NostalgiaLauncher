"""Chỉ phục vụ từng khối thuộc snapshot đã chọn; yêu cầu không chứa đường dẫn đĩa."""

import json
import re

from nostalgia.multiplayer.sync_model import SyncSnapshot

SYNC_CHUNK_BYTES = 256 * 1024


def read_sync_chunk(snapshot: SyncSnapshot | None, payload: bytes) -> bytes:
    if len(payload) > 1024:
        return b""
    try:
        document = json.loads(payload)
        request_id, digest = document["request_id"], document["sha256"]
        offset, length = document["offset"], document["length"]
        if not isinstance(request_id, str) or not re.fullmatch(r"[0-9a-f]{32}", request_id):
            return b""
        prefix = request_id.encode("ascii")
        failure = prefix + (b"\0" if length == 0 else b"")
        if (
            snapshot is None
            or not isinstance(digest, str)
            or type(offset) is not int
            or type(length) is not int
        ):
            return failure
        sync_file = next(
            (sync_file for sync_file in snapshot.manifest.files if sync_file.sha256 == digest), None
        )
        if (
            sync_file is None
            or not 0 <= length <= SYNC_CHUNK_BYTES
            or not 0 <= offset <= sync_file.size
            or offset + length > sync_file.size
        ):
            return failure
        path = snapshot.folder / sync_file.relative_path
        if path.is_symlink() or not path.is_file() or path.stat().st_size != sync_file.size:
            return failure
        with path.open("rb") as handle:
            handle.seek(offset)
            return prefix + handle.read(length)
    except (KeyError, ValueError, TypeError, OSError):
        return b""
