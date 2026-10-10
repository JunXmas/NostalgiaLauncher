"""Tải khối trực tiếp trong cửa sổ được backend cấp; kiểm hash trước khi trả file."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time

from nostalgia.errors import MultiplayerError, NetworkError
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_stream import PeerStream
from nostalgia.multiplayer.sync_chunk import SYNC_CHUNK_BYTES
from nostalgia.multiplayer.sync_model import SyncFile
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


class PeerDownload:
    def __init__(self, base_url: str, http_client: HttpClient) -> None:
        self._base_url, self._http = base_url, http_client
        self._stream: PeerStream | None = None
        self._expires = 0.0
        self._lock = asyncio.Lock()
        self._disabled = False

    async def download(
        self, room_code: str, sync_file: SyncFile, cancel_token: CancelToken
    ) -> bytes | None:
        if self._disabled:
            return None
        async with self._lock:
            cancel_token.raise_if_cancelled()
            try:
                if self._stream is None or time.monotonic() > self._expires:
                    await self.close()
                    self._stream = await connect_peer(self._base_url, room_code, "sync", self._http)
                    # Thời hạn phía host tính cả thời gian thương lượng ICE.
                    self._expires = time.monotonic() + 25
                async with asyncio.timeout(30):
                    parts = []
                    for offset in range(0, sync_file.size, SYNC_CHUNK_BYTES):
                        cancel_token.raise_if_cancelled()
                        length = min(SYNC_CHUNK_BYTES, sync_file.size - offset)
                        request_id = secrets.token_hex(16)
                        await self._stream.send(
                            json.dumps(
                                {
                                    "request_id": request_id,
                                    "sha256": sync_file.sha256,
                                    "offset": offset,
                                    "length": length,
                                }
                            ).encode()
                        )
                        payload = await self._stream.receive()
                        if not payload:
                            raise ConnectionError("peer transfer interrupted")
                        if payload[:32] != request_id.encode() or len(payload) != length + 32:
                            raise MultiplayerError(
                                "Khối đồng bộ trực tiếp không hợp lệ; không cài file."
                            )
                        parts.append(payload[32:])
                    payload = b"".join(parts)
                    if hashlib.sha256(payload).hexdigest() != sync_file.sha256:
                        raise MultiplayerError(
                            "File đồng bộ trực tiếp không khớp SHA-256; không cài file."
                        )
                    return payload
            except (ConnectionError, TimeoutError, NetworkError):
                await self.close()
                self._disabled = True
                return None
            except BaseException:
                await self.close()
                raise

    async def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            await stream.close()
