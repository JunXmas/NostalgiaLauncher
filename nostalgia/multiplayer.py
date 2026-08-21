"""Multiplayer LAN-qua-Internet, KHÔNG cần server thuê, KHÔNG cần mod, KHÔNG cần
người chơi cài đặt gì (chạy trong userspace của launcher), và **khác mạng vẫn chạy**.

Cơ chế (version-agnostic):
  • Host mở "Open to LAN" -> Minecraft phát multicast 224.0.2.60:4445 kèm cổng
    world. Launcher-host `detect_open_to_lan()` nghe được cổng đó, rồi `HostRelay`
    nối cổng world ra relay.
  • Người-vào: `TcpBridge` mở một cổng TCP local + `LanAnnouncer` phát multicast
    GIẢ trỏ về cổng ấy -> Minecraft vanilla tự hiện "world" trong tab LAN. Bấm
    Join: MC -> cổng local -> WSS -> relay -> host -> world.

Multicast chỉ chạy CỤC BỘ mỗi máy (không vượt Internet). Đường dữ liệu thật là
transport (WSS -> Cloudflare Durable Object): cả hai bên chỉ kết nối RA NGOÀI nên
2 người khác mạng / sau NAT vẫn thông, không cần mở port hay IP tĩnh.

Không thêm dependency: WS client là bản tối giản dựng trên asyncio + stdlib.
"""
from __future__ import annotations

import asyncio
import base64
import os
import re
import socket
import ssl
import struct
from typing import Awaitable, Callable, Optional
from urllib.parse import urlsplit

# Relay công khai đã deploy (Cloudflare Worker + Durable Object). Người chơi
# không cấu hình gì; đổi ở đây nếu tự host relay khác.
DEFAULT_RELAY = "wss://nostalgia-multiplayer-relay.junbob.workers.dev"

MC_GROUP = "224.0.2.60"
MC_PORT = 4445
_AD = re.compile(rb"\[AD\](\d+)\[/AD\]")
_MOTD = re.compile(rb"\[MOTD\](.*?)\[/MOTD\]", re.S)

# Flag của khung mux trên WS của host: [streamId:4 BE][flag:1][payload]
_DATA, _OPEN, _CLOSE = 0, 1, 2


# ─────────────────────────── LAN discovery (host side) ───────────────────────────

def detect_open_to_lan(timeout: float = 5.0) -> Optional[tuple[int, str]]:
    """Nghe multicast Minecraft; trả (port, motd) của world 'Open to LAN' thấy đầu
    tiên, hoặc None nếu hết giờ. Dùng ở máy HOST để biết cổng world vừa mở."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Minecraft (host) cũng bind 4445 để nghe LAN -> cần REUSEPORT để cùng nghe.
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
    try:
        s.bind(("", MC_PORT))
    except OSError:
        return None
    mreq = struct.pack("4sL", socket.inet_aton(MC_GROUP), socket.INADDR_ANY)
    s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    s.settimeout(timeout)
    try:
        data, _ = s.recvfrom(1024)
    except socket.timeout:
        return None
    finally:
        s.close()
    m = _AD.search(data)
    if not m:
        return None
    mo = _MOTD.search(data)
    motd = mo.group(1).decode("utf-8", "replace") if mo else "World"
    return int(m.group(1)), motd


# ─────────────────────────── LAN announce (joiner side) ──────────────────────────

class LanAnnouncer:
    """Phát multicast GIẢ mỗi ~1.5s để Minecraft vanilla trên máy người-vào hiện
    world bạn bè trong tab LAN, trỏ về `port` local mà launcher đang bắc cầu."""

    def __init__(self, port: int, motd: str = "§bNostalgia §7— Friend's world"):
        self.beacon = f"[MOTD]{motd}[/MOTD][AD]{port}[/AD]".encode("utf-8")
        self._task: Optional[asyncio.Task] = None

    async def _loop(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        try:
            while True:
                s.sendto(self.beacon, (MC_GROUP, MC_PORT))
                await asyncio.sleep(1.5)
        except asyncio.CancelledError:
            pass
        finally:
            s.close()

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.ensure_future(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


# ─────────────────────────────── Duplex (kênh 2 chiều) ───────────────────────────

class Duplex:
    """Kênh byte 2 chiều: recv() trả b'' khi hết, send() gửi, close() đóng.
    Cho phép TcpBridge dùng chung transport TCP thẳng hoặc WebSocket."""

    async def recv(self) -> bytes: raise NotImplementedError
    async def send(self, data: bytes) -> None: raise NotImplementedError
    async def close(self) -> None: raise NotImplementedError


class _StreamDuplex(Duplex):
    def __init__(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        self._r, self._w = r, w

    async def recv(self) -> bytes:
        try:
            return await self._r.read(65536)
        except (ConnectionError, asyncio.IncompleteReadError):
            return b""

    async def send(self, data: bytes) -> None:
        self._w.write(data)
        await self._w.drain()

    async def close(self) -> None:
        try:
            self._w.close()
        except Exception:
            pass


# ─────────────────────── WebSocket client tối giản (RFC 6455) ────────────────────

class _WSDuplex(Duplex):
    """WebSocket client chỉ đủ dùng: khung nhị phân, mask phía client, gộp
    fragment, tự trả pong, hiểu close. Không thêm thư viện ngoài."""

    def __init__(self, r: asyncio.StreamReader, w: asyncio.StreamWriter):
        self._r, self._w = r, w
        self._closed = False
        self._wlock = asyncio.Lock()   # serialize khung gửi (host mux nhiều stream)

    @classmethod
    async def connect(cls, url: str, timeout: float = 15.0) -> "_WSDuplex":
        u = urlsplit(url)
        secure = u.scheme == "wss"
        port = u.port or (443 if secure else 80)
        ctx = None
        if secure:
            ctx = ssl.create_default_context()
            # WS handshake kiểu Upgrade chỉ có ở HTTP/1.1 -> ép ALPN, tránh h2.
            ctx.set_alpn_protocols(["http/1.1"])
        # server_hostname (SNI) là bắt buộc để Cloudflare route đúng zone.
        r, w = await asyncio.wait_for(
            asyncio.open_connection(
                u.hostname, port, ssl=ctx,
                server_hostname=u.hostname if secure else None),
            timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        path = u.path or "/"
        if u.query:
            path += "?" + u.query
        req = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {u.hostname}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        w.write(req.encode())
        await w.drain()
        status = await asyncio.wait_for(r.readline(), timeout)
        if b"101" not in status:
            w.close()
            raise ConnectionError(f"WS handshake failed: {status!r}")
        while True:                       # nuốt hết header còn lại
            line = await r.readline()
            if line in (b"\r\n", b"", b"\n"):
                break
        return cls(r, w)

    def _frame(self, opcode: int, payload: bytes) -> bytes:
        fin_op = 0x80 | opcode
        n = len(payload)
        if n < 126:
            head = struct.pack("!BB", fin_op, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", fin_op, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", fin_op, 0x80 | 127, n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
        return head + mask + masked

    async def send(self, data: bytes) -> None:
        if self._closed:
            return
        async with self._wlock:
            self._w.write(self._frame(0x2, data))
            await self._w.drain()

    async def recv(self) -> bytes:
        buf = bytearray()
        while True:
            try:
                b0, b1 = struct.unpack("!BB", await self._r.readexactly(2))
            except (asyncio.IncompleteReadError, ConnectionError):
                return b""
            opcode = b0 & 0x0F
            ln = b1 & 0x7F
            if ln == 126:
                ln = struct.unpack("!H", await self._r.readexactly(2))[0]
            elif ln == 127:
                ln = struct.unpack("!Q", await self._r.readexactly(8))[0]
            mask = await self._r.readexactly(4) if b1 & 0x80 else b""
            payload = await self._r.readexactly(ln) if ln else b""
            if mask:
                payload = bytes(b ^ mask[i & 3] for i, b in enumerate(payload))
            if opcode == 0x8:             # close
                await self.close()
                return b""
            if opcode == 0x9:             # ping -> pong
                async with self._wlock:
                    self._w.write(self._frame(0xA, payload))
                    await self._w.drain()
                continue
            if opcode == 0xA:             # pong
                continue
            buf += payload
            if b0 & 0x80:                 # FIN
                return bytes(buf)

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            async with self._wlock:
                self._w.write(self._frame(0x8, b""))
                await self._w.drain()
        except Exception:
            pass
        try:
            self._w.close()
        except Exception:
            pass


# ─────────────────────────────── Cầu TCP local (joiner) ──────────────────────────

# Transport factory: mỗi kết nối Minecraft -> một Duplex tới đầu bên kia.
Transport = Callable[[], Awaitable[Duplex]]


class TcpBridge:
    """Mở cổng TCP local; mỗi kết nối Minecraft vào được nối song công với một
    Duplex (transport). Cổng trả về để `LanAnnouncer` quảng bá cho MC vanilla."""

    def __init__(self, transport: Transport, host: str = "127.0.0.1"):
        self._transport = transport
        self._host = host
        self._server: Optional[asyncio.AbstractServer] = None

    @property
    def port(self) -> int:
        return self._server.sockets[0].getsockname()[1] if self._server else 0

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._on_client, self._host, 0)
        return self.port

    async def _on_client(self, cr: asyncio.StreamReader, cw: asyncio.StreamWriter) -> None:
        try:
            dup = await self._transport()
        except Exception:
            cw.close()
            return
        await asyncio.gather(
            _tcp_to_dup(cr, dup), _dup_to_tcp(dup, cw), return_exceptions=True)
        await dup.close()
        try:
            cw.close()
        except Exception:
            pass

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None


async def _tcp_to_dup(r: asyncio.StreamReader, dup: Duplex) -> None:
    try:
        while (chunk := await r.read(65536)):
            await dup.send(chunk)
    except (ConnectionError, asyncio.IncompleteReadError):
        pass


async def _dup_to_tcp(dup: Duplex, w: asyncio.StreamWriter) -> None:
    try:
        while (chunk := await dup.recv()):
            w.write(chunk)
            await w.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass


def direct_transport(host: str, port: int) -> Transport:
    """Transport nối THẲNG tới host:port (test cục bộ / cùng LAN thật)."""
    async def _make() -> Duplex:
        r, w = await asyncio.open_connection(host, port)
        return _StreamDuplex(r, w)
    return _make


def ws_transport(relay_url: str, session: str) -> Transport:
    """Transport JOINER: mỗi kết nối MC mở một WS `role=join` tới relay.
    relay_url ví dụ 'wss://relay.example' -> nối 'wss://relay.example/s/<session>?role=join'."""
    base = relay_url.rstrip("/")
    async def _make() -> Duplex:
        return await _WSDuplex.connect(f"{base}/s/{session}?role=join")
    return _make


# ─────────────────────────────── Host mux (host side) ────────────────────────────

class HostRelay:
    """Máy HOST: một WS `role=host` tới relay; nhận khung mux, mỗi streamId mở một
    kết nối TCP tới world 'Open to LAN' (127.0.0.1:world_port) và bơm song công."""

    def __init__(self, relay_url: str, session: str, world_port: int):
        self._url = f"{relay_url.rstrip('/')}/s/{session}?role=host"
        self._world_port = world_port
        self._ws: Optional[_WSDuplex] = None
        self._streams: dict[int, asyncio.StreamWriter] = {}
        self._pumps: set[asyncio.Task] = set()
        self._task: Optional[asyncio.Task] = None

    async def _open_stream(self, sid: int) -> Optional[asyncio.StreamWriter]:
        try:
            r, w = await asyncio.open_connection("127.0.0.1", self._world_port)
        except OSError:
            return None
        self._streams[sid] = w
        t = asyncio.ensure_future(self._world_to_ws(sid, r))
        self._pumps.add(t)
        t.add_done_callback(self._pumps.discard)
        return w

    async def _world_to_ws(self, sid: int, r: asyncio.StreamReader) -> None:
        try:
            while (chunk := await r.read(65536)):
                await self._ws.send(struct.pack("!IB", sid, _DATA) + chunk)
        except (ConnectionError, asyncio.IncompleteReadError):
            pass
        finally:
            try:
                await self._ws.send(struct.pack("!IB", sid, _CLOSE))
            except Exception:
                pass

    def _close_stream(self, sid: int) -> None:
        w = self._streams.pop(sid, None)
        if w:
            try:
                w.close()
            except Exception:
                pass

    async def _run(self) -> None:
        self._ws = await _WSDuplex.connect(self._url)
        try:
            while (msg := await self._ws.recv()):
                if len(msg) < 5:
                    continue
                sid, flag = struct.unpack("!IB", msg[:5])
                payload = msg[5:]
                if flag == _CLOSE:
                    self._close_stream(sid)
                    continue
                w = self._streams.get(sid) or await self._open_stream(sid)
                if w is None:
                    continue
                if payload:
                    w.write(payload)
                    await w.drain()
        finally:
            for sid in list(self._streams):
                self._close_stream(sid)
            for t in list(self._pumps):
                t.cancel()
            await self._ws.close()

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.ensure_future(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
