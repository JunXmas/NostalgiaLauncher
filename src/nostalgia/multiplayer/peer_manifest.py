"""Chuyển chỉ mục theo khối qua DTLS; không đưa danh sách file lên Worker."""

import hashlib
import json
import re
import struct

from nostalgia.multiplayer.sync_manifest import manifest_document
from nostalgia.multiplayer.sync_model import SyncSnapshot

MANIFEST_CHUNK_BYTES = 64 * 1024
MAX_MANIFEST_BYTES = 2 * 1024**2


def read_manifest_chunk(snapshot: SyncSnapshot | None, payload: bytes) -> bytes:
    if snapshot is None or len(payload) > 1024:
        return b""
    try:
        request = json.loads(payload)
        request_id, offset = request["request_id"], request["offset"]
        if (
            request.get("kind") != "manifest"
            or not isinstance(request_id, str)
            or not re.fullmatch(r"[0-9a-f]{32}", request_id)
            or type(offset) is not int
            or offset < 0
            or offset % MANIFEST_CHUNK_BYTES
        ):
            return b""
        content = json.dumps(manifest_document(snapshot.manifest), separators=(",", ":")).encode()
        if not 0 < len(content) <= MAX_MANIFEST_BYTES or offset >= len(content):
            return b""
        return (
            request_id.encode()
            + struct.pack("!I", len(content))
            + hashlib.sha256(content).digest()
            + content[offset : offset + MANIFEST_CHUNK_BYTES]
        )
    except (KeyError, TypeError, ValueError):
        return b""
