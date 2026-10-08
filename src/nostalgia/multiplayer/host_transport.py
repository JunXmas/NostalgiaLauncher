"""Ghi khung ghép kênh; game và đồng bộ dùng chung một socket có khóa ghi."""

import asyncio
import contextlib

from nostalgia.multiplayer.mux import CLOSE, DATA, SYNC_DATA, pack_mux_frame
from nostalgia.multiplayer.sync_chunk import read_sync_chunk
from nostalgia.multiplayer.sync_model import SyncSnapshot
from nostalgia.net.websocket import WebSocketClient


class HostTransport:
    _socket: WebSocketClient | None
    sync_snapshot: SyncSnapshot | None

    async def _sync_chunk(self, payload: bytes) -> None:
        response = await asyncio.to_thread(read_sync_chunk, self.sync_snapshot, payload)
        if response and self._socket is not None:
            with contextlib.suppress(OSError, ConnectionError):
                await self._socket.send(pack_mux_frame(0, SYNC_DATA, response))

    async def _send(self, stream_id: int, payload: bytes) -> None:
        if self._socket is not None:
            with contextlib.suppress(OSError, ConnectionError):
                await self._socket.send(pack_mux_frame(stream_id, DATA, payload))

    async def _send_close(self, stream_id: int) -> None:
        if self._socket is not None:
            with contextlib.suppress(OSError, ConnectionError):
                await self._socket.send(pack_mux_frame(stream_id, CLOSE))
