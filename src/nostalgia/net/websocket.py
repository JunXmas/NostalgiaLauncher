"""WebSocket client tối giản (RFC 6455) trên asyncio + ssl, không thêm thư viện.

Đủ dùng cho relay: khung nhị phân, mask phía client, gộp fragment, trả pong, hiểu close.
Kiểm `Sec-WebSocket-Accept` (luật L9); trần khung và trần gộp 1 MiB (luật L5).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import secrets
import ssl
import struct
from urllib.parse import urlsplit

from nostalgia.errors import MultiplayerError

MAX_FRAME_BYTES = 1024 * 1024
# Tầng trên chỉ cần *kiểu* để tiêm chứng chỉ test; chỉ net/ được import ssl.
TlsContext = ssl.SSLContext
CONNECT_TIMEOUT_SECONDS = 15.0
_ACCEPT_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_BINARY, _CLOSE, _PING, _PONG = 0x2, 0x8, 0x9, 0xA


def expected_accept(key: str) -> str:
    return base64.b64encode(hashlib.sha1(key.encode() + _ACCEPT_GUID).digest()).decode()


class WebSocketClient:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
        self._closed = False
        self._write_lock = asyncio.Lock()  # host mux nhiều stream: khung không được xen nhau

    @property
    def closed(self) -> bool:
        return self._closed

    @classmethod
    async def connect(
        cls,
        url: str,
        *,
        timeout: float = CONNECT_TIMEOUT_SECONDS,
        tls_context: ssl.SSLContext | None = None,
    ) -> WebSocketClient:
        parts = urlsplit(url)
        secure = parts.scheme == "wss"
        if parts.scheme not in ("ws", "wss") or not parts.hostname:
            message = f"địa chỉ relay không hợp lệ: {url}"
            raise MultiplayerError(message)
        context = None
        if secure:
            context = tls_context or ssl.create_default_context()
            context.set_alpn_protocols(["http/1.1"])  # Upgrade chỉ có ở HTTP/1.1, tránh h2
        port = parts.port or (443 if secure else 80)
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    parts.hostname,
                    port,
                    ssl=context,
                    server_hostname=parts.hostname if secure else None,
                ),
                timeout,
            )
        except (OSError, TimeoutError) as exc:
            message = f"không nối được relay {parts.hostname}:{port}: {exc}"
            raise MultiplayerError(message) from exc
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        writer.write(
            (
                f"GET {path} HTTP/1.1\r\nHost: {parts.hostname}\r\n"
                "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            ).encode()
        )
        await writer.drain()
        try:
            await asyncio.wait_for(_read_upgrade(reader, key), timeout)
        except (MultiplayerError, TimeoutError, OSError):
            writer.close()
            raise
        return cls(reader, writer)

    async def send(self, payload: bytes) -> None:
        if self._closed:
            return
        async with self._write_lock:
            self._writer.write(_frame(_BINARY, payload))
            await self._writer.drain()

    async def receive(self) -> bytes:
        """Một thông điệp đã gộp; `b""` khi đầu kia đóng hoặc khung vượt trần."""
        assembled = bytearray()
        while True:
            try:
                first, second = struct.unpack("!BB", await self._reader.readexactly(2))
                length = second & 0x7F
                if length == 126:
                    length = struct.unpack("!H", await self._reader.readexactly(2))[0]
                elif length == 127:
                    length = struct.unpack("!Q", await self._reader.readexactly(8))[0]
                if length > MAX_FRAME_BYTES or len(assembled) + length > MAX_FRAME_BYTES:
                    await self.close()
                    return b""
                mask = await self._reader.readexactly(4) if second & 0x80 else b""
                payload = await self._reader.readexactly(length) if length else b""
            except (asyncio.IncompleteReadError, ConnectionError):
                self._closed = True
                return b""
            if mask:
                payload = _apply_mask(payload, mask)
            opcode = first & 0x0F
            if opcode == _CLOSE:
                await self.close()
                return b""
            if opcode == _PING:
                async with self._write_lock:
                    self._writer.write(_frame(_PONG, payload))
                    await self._writer.drain()
                continue
            if opcode == _PONG:
                continue
            assembled += payload
            if first & 0x80:
                return bytes(assembled)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            async with self._write_lock:
                self._writer.write(_frame(_CLOSE, b""))
                await self._writer.drain()
        except (OSError, ConnectionError):
            pass
        self._writer.close()


async def _read_upgrade(reader: asyncio.StreamReader, key: str) -> None:
    status = await reader.readline()
    if b" 101 " not in status:
        message = f"relay từ chối nâng cấp WebSocket: {status.strip().decode(errors='replace')}"
        raise MultiplayerError(message)
    accept = ""
    while True:
        line = await reader.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        header, _, value = line.decode(errors="replace").partition(":")
        if header.strip().lower() == "sec-websocket-accept":
            accept = value.strip()
    if accept != expected_accept(key):
        raise MultiplayerError("relay trả Sec-WebSocket-Accept sai: không phải WebSocket thật")


def _frame(opcode: int, payload: bytes) -> bytes:
    fin_opcode = 0x80 | opcode
    length = len(payload)
    if length < 126:
        head = struct.pack("!BB", fin_opcode, 0x80 | length)
    elif length < 65536:
        head = struct.pack("!BBH", fin_opcode, 0x80 | 126, length)
    else:
        head = struct.pack("!BBQ", fin_opcode, 0x80 | 127, length)
    mask = secrets.token_bytes(4)
    return head + mask + _apply_mask(payload, mask)


def _apply_mask(payload: bytes, mask: bytes) -> bytes:
    repeated = (mask * (len(payload) // 4 + 1))[: len(payload)]
    return bytes(a ^ b for a, b in zip(payload, repeated, strict=True))
