"""Tải khối trực tiếp trong cửa sổ được backend cấp; kiểm hash trước khi trả file."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import time

from nostalgia.errors import MultiplayerError, NetworkError
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_failure import PeerConnectionError
from nostalgia.multiplayer.peer_stream import PeerStream
from nostalgia.multiplayer.sync_chunk import SYNC_CHUNK_BYTES
from nostalgia.multiplayer.sync_model import SyncFile
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


class PeerDownload:
    def __init__(
        self, base_url: str, http_client: HttpClient, *, disable_on_failure: bool = True
    ) -> None:
        self._base_url, self._http = base_url, http_client
        self._stream: PeerStream | None = None
        self._expires = 0.0
        self._room_code = ""
        self._lock = asyncio.Lock()
        self._disabled = False
        self._disable_on_failure = disable_on_failure

    async def download(
        self, room_code: str, sync_file: SyncFile, cancel_token: CancelToken
    ) -> bytes | None:
        if self._disabled:
            return None
        async with self._lock:
            cancel_token.raise_if_cancelled()
            try:
                if self._room_code != room_code:
                    await self.close()
                    self._room_code = room_code
                parts = []
                for offset in range(0, sync_file.size, SYNC_CHUNK_BYTES):
                    parts.append(await self._chunk(room_code, sync_file, offset, cancel_token))
                payload = b"".join(parts)
                if hashlib.sha256(payload).hexdigest() != sync_file.sha256:
                    raise MultiplayerError(
                        "File đồng bộ trực tiếp không khớp SHA-256; không cài file."
                    )
                return payload
            except PeerConnectionError as exc:
                await self.close()
                if not self._disable_on_failure or not exc.retryable:
                    raise
                self._disabled = True
                return None
            except (ConnectionError, TimeoutError, NetworkError) as exc:
                await self.close()
                self._disabled = self._disable_on_failure
                if not self._disable_on_failure:
                    raise PeerConnectionError(
                        "Đường truyền đồng bộ P2P đã ngắt. "
                        "Hãy thử đồng bộ lại; bản chơi chưa bị thay đổi."
                    ) from exc
                return None
            except BaseException:
                await self.close()
                raise

    async def _chunk(
        self, room_code: str, sync_file: SyncFile, offset: int, cancel_token: CancelToken
    ) -> bytes:
        length = min(SYNC_CHUNK_BYTES, sync_file.size - offset)
        for attempt in range(2):
            cancel_token.raise_if_cancelled()
            if self._stream is None or self._stream.closed or time.monotonic() >= self._expires:
                await self.close()
                started_at = time.monotonic()
                self._stream = await connect_peer(self._base_url, room_code, "sync", self._http)
                # Mỗi kênh mới kiểm tra lại quyền ở backend. Không kéo dài quyền cũ.
                self._expires = started_at + 25
            request_id = secrets.token_hex(16)
            try:
                # Trần cho từng khối đang chờ, thay vì cắt cả file sau 30 giây.
                async with asyncio.timeout(30):
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
                cancel_token.raise_if_cancelled()
                if payload[:32] != request_id.encode() or len(payload) != length + 32:
                    raise MultiplayerError("Khối đồng bộ trực tiếp không hợp lệ; không cài file.")
                return payload[32:]
            except (ConnectionError, TimeoutError):
                await self.close()
                if attempt == 1:
                    raise
        raise AssertionError("unreachable peer retry")

    async def close(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            await stream.close()
