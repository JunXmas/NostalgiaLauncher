"""Phía JOINER: proxy TCP cục bộ. Minecraft nối vào `127.0.0.1:<local_port>`, mỗi kết nối mở
một WebSocket `role=join` tới relay, bắt tay bằng `JoinerGate`, rồi bơm byte hai chiều.

Bind cứng loopback, cổng do hệ điều hành cấp (luật L7). Bắt tay hỏng → đóng, không hạ cấp.
"""

from __future__ import annotations

import asyncio
import contextlib

from nostalgia.multiplayer.gate import JoinerGate
from nostalgia.multiplayer.handshake import HANDSHAKE_TIMEOUT_SECONDS
from nostalgia.net.websocket import TlsContext, WebSocketClient

READ_CHUNK = 65536


class JoinerBridge:
    def __init__(
        self,
        relay_url: str,
        room_id: str,
        room_secret: str,
        *,
        tls_context: TlsContext | None = None,
    ) -> None:
        self._url = f"{relay_url.rstrip('/')}/s/{room_id}?role=join"
        self._room_secret = room_secret
        self._tls_context = tls_context
        self._server: asyncio.AbstractServer | None = None
        self._handlers: set[asyncio.Task[None]] = set()

    @property
    def local_port(self) -> int:
        if self._server is None:
            return 0
        sockets = getattr(self._server, "sockets", ())
        return int(sockets[0].getsockname()[1]) if sockets else 0

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._serve, "127.0.0.1", 0)
        return self.local_port

    async def probe(self) -> None:
        """Nối thử relay + bắt tay một lần để báo lỗi (sai mã, host tắt) ngay khi bấm VÀO."""
        socket = await WebSocketClient.connect(self._url, tls_context=self._tls_context)
        try:
            await self._handshake(socket)
        finally:
            await socket.close()

    async def stop(self) -> None:
        for handler in list(self._handlers):
            handler.cancel()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _serve(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        task = asyncio.current_task()
        if task is not None:
            self._handlers.add(task)
            task.add_done_callback(self._handlers.discard)
        try:
            socket = await WebSocketClient.connect(self._url, tls_context=self._tls_context)
        except Exception:
            writer.close()
            return
        try:
            leftover = await self._handshake(socket)
            if leftover:
                writer.write(leftover)
                await writer.drain()
            await asyncio.gather(
                _pump_game_to_relay(reader, socket),
                _pump_relay_to_game(socket, writer),
                return_exceptions=True,
            )
        except Exception:
            pass
        finally:
            await socket.close()
            writer.close()

    async def _handshake(self, socket: WebSocketClient) -> bytes:
        gate = JoinerGate(self._room_secret)
        await socket.send(gate.hello())
        while True:
            try:
                chunk = await asyncio.wait_for(socket.receive(), HANDSHAKE_TIMEOUT_SECONDS)
            except TimeoutError:
                raise ConnectionError("host không trả lời bắt tay") from None
            if not chunk:
                raise ConnectionError("relay đóng giữa bắt tay: sai mã phòng hoặc host đã tắt")
            step = gate.feed(chunk)
            if step.verdict == "rejected":
                raise ConnectionError("host không chứng minh được giữ mã phòng")
            if step.verdict == "accepted":
                await socket.send(step.reply)
                return step.forward


async def _pump_game_to_relay(reader: asyncio.StreamReader, socket: WebSocketClient) -> None:
    with contextlib.suppress(ConnectionError, asyncio.IncompleteReadError):
        while chunk := await reader.read(READ_CHUNK):
            await socket.send(chunk)
    await socket.close()


async def _pump_relay_to_game(socket: WebSocketClient, writer: asyncio.StreamWriter) -> None:
    with contextlib.suppress(ConnectionError, OSError):
        while chunk := await socket.receive():
            writer.write(chunk)
            await writer.drain()
    writer.close()
