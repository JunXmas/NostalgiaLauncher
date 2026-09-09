"""Relay giả trên loopback: WebSocket server thuần asyncio, ghép host↔joiner y hệt Durable Object.

Đủ để chạy trọn đường host → relay → joiner trong test mà không chạm Internet. Ghi lại mọi
byte đi qua để khẳng định secret không bao giờ lên dây.
"""

from __future__ import annotations

import asyncio
import contextlib
import struct
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlsplit

from nostalgia.multiplayer.mux import CLOSE, DATA, OPEN, pack_mux_frame, unpack_mux_frame
from nostalgia.net.websocket import expected_accept


@dataclass
class Room:
    host: ServerSocket | None = None
    joiners: dict[int, ServerSocket] = field(default_factory=dict)
    next_stream_id: int = 1


class ServerSocket:
    """Phía server của một WebSocket: khung tới có mask, khung đi không mask."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader, self.writer = reader, writer
        self.closed = False

    async def receive(self) -> bytes:
        try:
            first, second = struct.unpack("!BB", await self.reader.readexactly(2))
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", await self.reader.readexactly(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", await self.reader.readexactly(8))[0]
            mask = await self.reader.readexactly(4) if second & 0x80 else b""
            payload = await self.reader.readexactly(length)
        except (asyncio.IncompleteReadError, ConnectionError):
            return b""
        if mask:
            payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        if first & 0x0F == 0x8:
            return b""
        return payload

    async def send(self, payload: bytes, opcode: int = 0x2) -> None:
        if self.closed:
            return
        length = len(payload)
        if length < 126:
            head = struct.pack("!BB", 0x80 | opcode, length)
        elif length < 65536:
            head = struct.pack("!BBH", 0x80 | opcode, 126, length)
        else:
            head = struct.pack("!BBQ", 0x80 | opcode, 127, length)
        self.writer.write(head + payload)
        await self.writer.drain()

    def close(self) -> None:
        self.closed = True
        self.writer.close()


class FakeRelay:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self.wire: bytearray = bytearray()  # mọi payload đã đi qua relay
        self._server: asyncio.AbstractServer | None = None
        self.port = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._serve, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    @property
    def url(self) -> str:
        return f"ws://127.0.0.1:{self.port}"

    async def stop(self) -> None:
        """Đóng mọi socket rồi chờ có hạn: `wait_closed()` (3.12) chờ tất cả handler kết thúc."""
        for room in self.rooms.values():
            for joiner in list(room.joiners.values()):
                joiner.close()
            if room.host is not None:
                room.host.close()
        if self._server:
            self._server.close()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._server.wait_closed(), 1)

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        request_line = (await reader.readline()).decode()
        headers: dict[str, str] = {}
        while (line := await reader.readline()) not in (b"\r\n", b""):
            header, _, value = line.decode().partition(":")
            headers[header.strip().lower()] = value.strip()
        target = request_line.split(" ")[1]
        parts = urlsplit(target)
        room_id = parts.path.rsplit("/", 1)[-1]
        role = parse_qs(parts.query).get("role", [""])[0]
        writer.write(
            (
                "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {expected_accept(headers['sec-websocket-key'])}\r\n\r\n"
            ).encode()
        )
        await writer.drain()
        server_socket = ServerSocket(reader, writer)
        room = self.rooms.setdefault(room_id, Room())
        if role == "host":
            await self._run_host(room, server_socket)
        else:
            await self._run_joiner(room, server_socket)

    async def _run_host(self, room: Room, host: ServerSocket) -> None:
        if room.host is not None:
            host.close()
            return
        room.host = host
        try:
            while frame := await host.receive():
                self.wire += frame
                unpacked = unpack_mux_frame(frame)
                if unpacked is None:
                    continue
                stream_id, flag, payload = unpacked
                joiner = room.joiners.get(stream_id)
                if joiner is None:
                    continue
                if flag == DATA:
                    await joiner.send(payload)
                elif flag == CLOSE:
                    room.joiners.pop(stream_id, None)
                    joiner.close()
        finally:
            room.host = None
            for joiner in room.joiners.values():
                joiner.close()
            room.joiners.clear()

    async def _run_joiner(self, room: Room, joiner: ServerSocket) -> None:
        if room.host is None:
            joiner.close()
            return
        stream_id = room.next_stream_id
        room.next_stream_id += 1
        room.joiners[stream_id] = joiner
        await room.host.send(pack_mux_frame(stream_id, OPEN))
        try:
            while payload := await joiner.receive():
                self.wire += payload
                await room.host.send(pack_mux_frame(stream_id, DATA, payload))
        finally:
            if room.joiners.pop(stream_id, None) is not None and room.host is not None:
                await room.host.send(pack_mux_frame(stream_id, CLOSE))
