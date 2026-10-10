"""Ghi khung ghép kênh; game và đồng bộ dùng chung một socket có khóa ghi."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable

from nostalgia.multiplayer.gate import HostGate
from nostalgia.multiplayer.mux import CLOSE, DATA, SYNC_DATA, pack_mux_frame
from nostalgia.multiplayer.sync_chunk import read_sync_chunk
from nostalgia.multiplayer.sync_model import SyncSnapshot
from nostalgia.net.binary_socket import BinarySocket, DirectHost


class HostTransport:
    _gates: dict[int, HostGate]
    _deadlines: dict[int, asyncio.TimerHandle]
    _socket: BinarySocket | None
    sync_snapshot: SyncSnapshot | None
    peer: DirectHost | None
    _on_joiners_changed: Callable[[int], None] | None
    _world_port: int
    _room_secret: str
    _max_joiners: int
    _worlds: dict[int, asyncio.StreamWriter]

    @property
    def joiner_count(self) -> int:
        return len(self._worlds) + (self.peer.joiner_count if self.peer else 0)

    @property
    def world_port(self) -> int:
        return self._world_port

    @property
    def room_secret(self) -> str:
        return self._room_secret

    @property
    def max_joiners(self) -> int:
        return self._max_joiners

    def _full(self) -> bool:
        return self.joiner_count >= self._max_joiners

    def set_world_port(self, world_port: int) -> None:
        self._world_port = world_port

    @property
    def sync_ticket(self) -> str:
        return self._socket.host_ticket if self._socket is not None else ""

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

    def _notify(self) -> None:
        if self._on_joiners_changed is not None:
            self._on_joiners_changed(self.joiner_count)

    def _forget_gate(self, stream_id: int) -> None:
        self._gates.pop(stream_id, None)
        deadline = self._deadlines.pop(stream_id, None)
        if deadline is not None:
            deadline.cancel()
