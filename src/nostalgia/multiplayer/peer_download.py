"""Tải khối trực tiếp trong cửa sổ được backend cấp; kiểm hash trước khi trả file."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import struct
import time

from nostalgia.errors import MultiplayerError, NetworkError
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_failure import PeerConnectionError
from nostalgia.multiplayer.peer_manifest import MANIFEST_CHUNK_BYTES, MAX_MANIFEST_BYTES
from nostalgia.multiplayer.peer_stream import PeerStream
from nostalgia.multiplayer.sync_chunk import SYNC_CHUNK_BYTES
from nostalgia.multiplayer.sync_manifest import parse_sync_manifest
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
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
        payload = await self._exchange(
            room_code,
            {"sha256": sync_file.sha256, "offset": offset, "length": length},
            cancel_token,
        )
        if len(payload) != length:
            raise MultiplayerError("Khối đồng bộ trực tiếp không hợp lệ; không cài file.")
        return payload

    async def fetch_manifest(self, room_code: str, cancel_token: CancelToken) -> SyncManifest:
        async with self._lock:
            if self._room_code != room_code:
                await self.close()
                self._room_code = room_code
            try:
                return await self._fetch_manifest(room_code, cancel_token)
            except BaseException:
                await self.close()
                raise

    async def _fetch_manifest(self, room_code: str, cancel_token: CancelToken) -> SyncManifest:
        content = bytearray()
        expected_size, digest = 0, b""
        while True:
            reply = await self._exchange(
                room_code, {"kind": "manifest", "offset": len(content)}, cancel_token
            )
            if len(reply) < 37:
                raise MultiplayerError("Chỉ mục modpack của phòng bị thiếu.")
            size, received_digest, chunk = (
                struct.unpack("!I", reply[:4])[0],
                reply[4:36],
                reply[36:],
            )
            if not 0 < size <= MAX_MANIFEST_BYTES or len(chunk) != min(
                MANIFEST_CHUNK_BYTES, size - len(content)
            ):
                raise MultiplayerError("Chỉ mục modpack vượt giới hạn hoặc sai kích thước.")
            if expected_size and (expected_size != size or digest != received_digest):
                raise MultiplayerError("Modpack của chủ phòng đã thay đổi; hãy thử lại.")
            expected_size, digest = size, received_digest
            content.extend(chunk)
            if len(content) == size:
                break
        if hashlib.sha256(content).digest() != digest:
            raise MultiplayerError("Chỉ mục modpack không khớp SHA-256.")
        return parse_sync_manifest(decode_json(bytes(content), what="modpack của phòng"))

    async def _exchange(
        self, room_code: str, document: dict[str, str | int], cancel_token: CancelToken
    ) -> bytes:
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
                        json.dumps({"request_id": request_id, **document}).encode()
                    )
                    payload = await self._stream.receive()
                    if not payload:
                        raise ConnectionError("peer transfer interrupted")
                cancel_token.raise_if_cancelled()
                if payload[:32] != request_id.encode():
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
