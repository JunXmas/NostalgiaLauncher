"""Luồng WebRTC có khung, hàng đợi giới hạn và áp lực ngược cho game/file."""

from __future__ import annotations

import asyncio
import contextlib
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiortc import RTCDataChannel, RTCPeerConnection

MAX_PEER_PAYLOAD = 256 * 1024 + 64
PEER_FRAME_BYTES = 16384
MAX_BUFFERED_BYTES = 256 * 1024


class PeerStream:
    host_ticket = ""

    def __init__(self, connection: RTCPeerConnection, channel: RTCDataChannel) -> None:
        self.connection, self.channel = connection, channel
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=16)
        self._buffer = bytearray()
        self._open, self._writable = asyncio.Event(), asyncio.Event()
        self._closed = False
        self._send_lock = asyncio.Lock()
        self._credit = asyncio.Event()
        self._credit.set()
        self._outstanding = 0
        channel.bufferedAmountLowThreshold = MAX_BUFFERED_BYTES // 2
        channel.on("open", self._open.set)
        channel.on("close", self._ended)
        channel.on("message", self._message)
        channel.on("bufferedamountlow", self._writable.set)
        if channel.readyState == "open":
            self._open.set()

    @property
    def closed(self) -> bool:
        return self._closed

    async def wait_open(self, timeout: float = 12) -> None:
        await asyncio.wait_for(self._open.wait(), timeout)
        if self._closed or self.channel.readyState != "open":
            raise ConnectionError("peer channel closed")

    def _message(self, payload: bytes | str) -> None:
        if self._closed:
            return
        if not isinstance(payload, bytes) or len(payload) > PEER_FRAME_BYTES:
            self.channel.close()
            self._ended()
            return
        self._buffer.extend(payload)
        while len(self._buffer) >= 4:
            length = struct.unpack_from("!I", self._buffer)[0]
            if length == 0:
                if not self._outstanding:
                    self.channel.close()
                    self._ended()
                    return
                del self._buffer[:4]
                self._outstanding -= 1
                self._credit.set()
                continue
            if length > MAX_PEER_PAYLOAD:
                self.channel.close()
                self._ended()
                return
            if len(self._buffer) < length + 4:
                return
            message = bytes(self._buffer[4 : length + 4])
            del self._buffer[: length + 4]
            try:
                self._queue.put_nowait(message)
            except asyncio.QueueFull:
                self.channel.close()
                self._ended()
                return

    def _ended(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._buffer.clear()
        self._open.set()
        self._writable.set()
        self._credit.set()
        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(None)

    async def send(self, payload: bytes) -> None:
        if not 0 < len(payload) <= MAX_PEER_PAYLOAD:
            raise ValueError("invalid peer frame length")
        while self._outstanding >= 16 and not self._closed:
            await asyncio.wait_for(self._credit.wait(), 15)
        if self._closed:
            raise ConnectionError("peer channel closed")
        self._outstanding += 1
        if self._outstanding >= 16:
            self._credit.clear()
        try:
            async with self._send_lock:
                framed = struct.pack("!I", len(payload)) + payload
                for offset in range(0, len(framed), PEER_FRAME_BYTES):
                    while self.channel.bufferedAmount > MAX_BUFFERED_BYTES and not self._closed:
                        self._writable.clear()
                        if self.channel.bufferedAmount <= MAX_BUFFERED_BYTES:
                            break
                        await asyncio.wait_for(self._writable.wait(), 10)
                    if self._closed or self.channel.readyState != "open":
                        raise ConnectionError("peer channel closed")
                    self.channel.send(framed[offset : offset + PEER_FRAME_BYTES])
        except BaseException:
            await self.close()
            raise

    async def receive(self) -> bytes:
        if self._closed and self._queue.empty():
            return b""
        payload = await self._queue.get() or b""
        if payload and not self._closed:
            async with self._send_lock:
                if not self._closed:
                    self.channel.send(struct.pack("!I", 0))
        return payload

    async def close(self) -> None:
        self._ended()
        await asyncio.shield(self.connection.close())
