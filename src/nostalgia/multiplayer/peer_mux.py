"""Dùng chung một kết nối DTLS cho các lần Minecraft ping và đăng nhập."""

from __future__ import annotations

import asyncio
import contextlib

from nostalgia.multiplayer.mux import CLOSE, DATA, pack_mux_frame, unpack_mux_frame
from nostalgia.multiplayer.peer_stream import PeerStream


class PeerSocket:
    host_ticket = ""

    def __init__(self, mux: PeerMux, stream_id: int) -> None:
        self._mux, self._id = mux, stream_id
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=16)
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    async def send(self, payload: bytes) -> None:
        if self._closed:
            raise ConnectionError("peer stream closed")
        await self._mux.stream.send(pack_mux_frame(self._id, DATA, payload))

    async def receive(self) -> bytes:
        if self._closed and self._queue.empty():
            return b""
        return await self._queue.get() or b""

    def end(self) -> None:
        self._closed = True
        with contextlib.suppress(asyncio.QueueFull):
            self._queue.put_nowait(None)
        self._mux.sockets.pop(self._id, None)

    async def close(self) -> None:
        if not self._closed:
            self.end()
            with contextlib.suppress(ConnectionError, TimeoutError):
                await self._mux.stream.send(pack_mux_frame(self._id, CLOSE))


class PeerMux:
    def __init__(self, stream: PeerStream) -> None:
        self.stream = stream
        self.sockets: dict[int, PeerSocket] = {}
        self._next_id = 1
        self.closed = False
        self._runner = asyncio.create_task(self._run())

    def open(self) -> PeerSocket:
        if self.closed or len(self.sockets) >= 16 or self._next_id >= 2**32:
            raise ConnectionError("peer transport unavailable")
        stream_id = self._next_id
        self._next_id += 1
        socket = PeerSocket(self, stream_id)
        self.sockets[stream_id] = socket
        return socket

    async def _run(self) -> None:
        try:
            while payload := await self.stream.receive():
                frame = unpack_mux_frame(payload)
                if frame is None:
                    break
                stream_id, flag, body = frame
                socket = self.sockets.get(stream_id)
                if socket is None:
                    continue
                if flag == CLOSE:
                    socket.end()
                elif flag == DATA:
                    await socket._queue.put(body)
        finally:
            self.closed = True
            for socket in tuple(self.sockets.values()):
                socket.end()

    async def close(self) -> None:
        self._runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._runner
        await self.stream.close()
