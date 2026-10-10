"""Kiểm file trực tiếp trước khi gateway trả dữ liệu cho giao dịch cài modpack."""

import hashlib
from collections.abc import Callable

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.sync_model import SyncFile
from nostalgia.operations.cancellation import CancelToken


def fetch_peer_file(
    download_peer: Callable[[str, SyncFile, CancelToken], bytes | None] | None,
    room_code: str,
    sync_file: SyncFile,
    cancel_token: CancelToken | None,
) -> bytes | None:
    if download_peer is None:
        return None
    cancel_token = cancel_token or CancelToken()
    cancel_token.raise_if_cancelled()
    payload = download_peer(room_code, sync_file, cancel_token)
    cancel_token.raise_if_cancelled()
    if payload is not None and (
        len(payload) != sync_file.size or hashlib.sha256(payload).hexdigest() != sync_file.sha256
    ):
        raise MultiplayerError("File đồng bộ trực tiếp không khớp SHA-256; không cài file.")
    return payload
