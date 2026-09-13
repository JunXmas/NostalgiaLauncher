"""Phía HOST: một WebSocket tới relay, mỗi stream là một joiner → một kết nối tới world.

Stream chỉ được chạm world sau khi `HostGate` chấp nhận (bắt tay + gói Minecraft đầu). Trần:
≤ MAX_PENDING stream chưa xác thực, timeout bắt tay, ≤ max_joiners joiner (luật L5); phòng
khoá thì từ chối stream mới (luật L6). Host chỉ nối `127.0.0.1:world_port` (luật L7).
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable

from nostalgia.multiplayer.gate import HostGate
from nostalgia.multiplayer.handshake import HANDSHAKE_TIMEOUT_SECONDS
from nostalgia.multiplayer.mux import CLOSE, DATA, pack_mux_frame, unpack_mux_frame
from nostalgia.net.websocket import TlsContext, WebSocketClient

MAX_PENDING = 32
MAX_JOINERS = 16
READ_CHUNK = 65536
SEND_QUEUE_SIZE = 128


class HostRelay:
    def __init__(
        self,
        relay_url: str,
        room_id: str,
        room_secret: str,
        world_port: int,
        *,
        tls_context: TlsContext | None = None,
        max_joiners: int = MAX_JOINERS,
        on_joiners_changed: Callable[[int], None] | None = None,
    ) -> None:
        self._url = f"{relay_url.rstrip('/')}/s/{room_id}?role=host"
        self._room_secret = room_secret
        self._world_port = world_port
        self._tls_context = tls_context
        self._max_joiners = max_joiners
        self._on_joiners_changed = on_joiners_changed
        self._socket: WebSocketClient | None = None
        self._gates: dict[int, HostGate] = {}
        self._deadlines: dict[int, asyncio.TimerHandle] = {}
        self._worlds: dict[int, asyncio.StreamWriter] = {}
        self._write_queues: dict[int, asyncio.Queue[bytes | None]] = {}
        self._write_pumps: set[asyncio.Task[None]] = set()
        self._pumps: set[asyncio.Task[None]] = set()
        self._runner: asyncio.Task[None] | None = None
        self.locked = False

    @property
    def joiner_count(self) -> int:
        return len(self._worlds)

    async def connect(self) -> None:
        """Nối relay trước khi báo "đang host" để lỗi ném ra chỗ gọi, không chết lặng."""
        self._socket = await WebSocketClient.connect(self._url, tls_context=self._tls_context)

    async def run(self) -> None:
        assert self._socket is not None, "gọi connect() trước"
        try:
            while frame := await self._socket.receive():
                unpacked = unpack_mux_frame(frame)
                if unpacked is None:
                    continue
                stream_id, flag, payload = unpacked
                if flag == CLOSE:
                    self._drop(stream_id)
                elif stream_id in self._worlds:
                    await self._to_world(stream_id, payload)
                elif payload:
                    await self._gate(stream_id, payload)
        finally:
            await self.close()

    def start(self) -> None:
        self._runner = asyncio.ensure_future(self.run())

    async def stop(self) -> None:
        """Huỷ vòng nhận; `run()` tự dọn stream và đóng WebSocket trong `finally`."""
        if self._runner is None or self._runner.done():
            await self.close()
            return
        self._runner.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._runner

    async def close(self) -> None:
        for stream_id in list(self._gates) + list(self._worlds):
            self._drop(stream_id)
        for pump in list(self._pumps):
            pump.cancel()
        for pump in list(self._write_pumps):
            pump.cancel()
        if self._socket is not None:
            await self._socket.close()

    # ----- cửa xác thực -----

    async def _gate(self, stream_id: int, payload: bytes) -> None:
        gate = self._gates.get(stream_id)
        if gate is None:
            if self.locked or len(self._gates) >= MAX_PENDING or self._full():
                await self._send_close(stream_id)
                return
            gate = self._gates[stream_id] = HostGate(self._room_secret)
            self._deadlines[stream_id] = asyncio.get_running_loop().call_later(
                HANDSHAKE_TIMEOUT_SECONDS, self._expire, stream_id
            )
        step = gate.feed(payload)
        if step.reply:
            await self._send(stream_id, step.reply)
        if step.verdict == "rejected":
            self._drop(stream_id)
            await self._send_close(stream_id)
        elif step.verdict == "accepted":
            self._forget_gate(stream_id)
            if await self._open_world(stream_id):
                await self._to_world(stream_id, step.forward)
            else:
                await self._send_close(stream_id)

    def _full(self) -> bool:
        return len(self._worlds) >= self._max_joiners

    def _expire(self, stream_id: int) -> None:
        if stream_id in self._gates:
            self._drop(stream_id)
            closing = asyncio.ensure_future(self._send_close(stream_id))
            self._pumps.add(closing)
            closing.add_done_callback(self._pumps.discard)

    def _forget_gate(self, stream_id: int) -> None:
        self._gates.pop(stream_id, None)
        deadline = self._deadlines.pop(stream_id, None)
        if deadline is not None:
            deadline.cancel()

    # ----- world -----

    async def _open_world(self, stream_id: int) -> bool:
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", self._world_port)
        except OSError:
            return False
        self._worlds[stream_id] = writer
        queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=SEND_QUEUE_SIZE)
        self._write_queues[stream_id] = queue
        write_pump = asyncio.ensure_future(self._write_pump_for(stream_id, writer, queue))
        self._write_pumps.add(write_pump)
        write_pump.add_done_callback(self._write_pumps.discard)
        pump = asyncio.ensure_future(self._from_world(stream_id, reader))
        self._pumps.add(pump)
        pump.add_done_callback(self._pumps.discard)
        self._notify()
        return True

    async def _to_world(self, stream_id: int, payload: bytes) -> None:
        queue = self._write_queues.get(stream_id)
        if queue is None or not payload:
            return
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            self._drop(stream_id)
            await self._send_close(stream_id)

    async def _write_pump_for(
        self, stream_id: int, writer: asyncio.StreamWriter, queue: asyncio.Queue[bytes | None]
    ) -> None:
        """Ghi dữ liệu từ hàng đợi vào TCP writer riêng cho mỗi client.

        Nếu drain() bị chặn do TCP buffer đầy, chỉ client này bị ảnh hưởng —
        vòng dispatch chính và các client khác vẫn chạy bình thường.
        """
        try:
            while True:
                payload = await queue.get()
                if payload is None:
                    break
                try:
                    writer.write(payload)
                    await writer.drain()
                except (ConnectionError, OSError):
                    break
        finally:
            if stream_id in self._worlds:
                self._drop(stream_id)
                await self._send_close(stream_id)

    async def _from_world(self, stream_id: int, reader: asyncio.StreamReader) -> None:
        try:
            while chunk := await reader.read(READ_CHUNK):
                await self._send(stream_id, chunk)
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            if stream_id in self._worlds:
                self._drop(stream_id)
                await self._send_close(stream_id)

    def _drop(self, stream_id: int) -> None:
        self._forget_gate(stream_id)
        writer = self._worlds.pop(stream_id, None)
        queue = self._write_queues.pop(stream_id, None)
        if queue is not None:
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(None)
        if writer is not None:
            writer.close()
            self._notify()

    def _notify(self) -> None:
        if self._on_joiners_changed is not None:
            self._on_joiners_changed(len(self._worlds))

    async def _send(self, stream_id: int, payload: bytes) -> None:
        if self._socket is not None:
            with contextlib.suppress(OSError, ConnectionError):
                await self._socket.send(pack_mux_frame(stream_id, DATA, payload))

    async def _send_close(self, stream_id: int) -> None:
        if self._socket is not None:
            with contextlib.suppress(OSError, ConnectionError):
                await self._socket.send(pack_mux_frame(stream_id, CLOSE))
