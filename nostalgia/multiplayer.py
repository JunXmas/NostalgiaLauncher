"""Multiplayer LAN-qua-Internet, KHÔNG cần server thuê, KHÔNG cần mod, KHÔNG cần
người chơi cài đặt gì (chạy trong userspace của launcher).

Cơ chế (version-agnostic):
  • Host mở "Open to LAN" -> Minecraft phát multicast 224.0.2.60:4445 kèm cổng
    world. Launcher-host `detect_open_to_lan()` nghe được cổng đó.
  • Người-vào: launcher mở một cổng TCP local + `LanAnnouncer` phát multicast GIẢ
    trỏ về cổng local ấy -> Minecraft vanilla tự hiện "world" trong tab LAN. Bấm
    Join, traffic đi: MC -> cổng local -> cầu (relay) -> launcher-host -> world.

Module này lo phần CLIENT thuần local: dò/giả LAN (`detect_open_to_lan`,
`LanAnnouncer`) và cầu TCP local (`TcpBridge`). Đường relay (WebSocket tới
Cloudflare Durable Object) và lớp bạn bè/invite nằm ở phần khác — `TcpBridge`
nhận một "transport factory" nên cắm relay vào sau mà không đổi client.
"""
from __future__ import annotations

import asyncio
import re
import socket
import struct
from typing import Awaitable, Callable

MC_GROUP = "224.0.2.60"
MC_PORT = 4445
_AD = re.compile(rb"\[AD\](\d+)\[/AD\]")
_MOTD = re.compile(rb"\[MOTD\](.*?)\[/MOTD\]", re.S)


# ─────────────────────────── LAN discovery (host side) ───────────────────────────

def detect_open_to_lan(timeout: float = 5.0) -> tuple[int, str] | None:
    """Nghe multicast Minecraft; trả (port, motd) của world 'Open to LAN' thấy đầu
    tiên, hoặc None nếu hết giờ. Dùng ở máy HOST để biết cổng world vừa mở."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
        self._sock: socket.socket | None = None
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        self._sock = s
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


# ─────────────────────────────── Cầu TCP local ──────────────────────────────────

# transport = (reader, writer) tới đầu bên kia (relay/host). Factory tạo mới mỗi
# kết nối Minecraft. Ở test cục bộ ta cắm factory nối thẳng tới một host:port.
Transport = Callable[[], Awaitable[tuple[asyncio.StreamReader, asyncio.StreamWriter]]]


class TcpBridge:
    """Mở cổng TCP local; mỗi kết nối Minecraft vào được nối song công với một
    transport (relay tới máy host). Trả về cổng đã mở để `LanAnnouncer` quảng bá."""

    def __init__(self, transport: Transport, host: str = "127.0.0.1"):
        self._transport = transport
        self._host = host
        self._server: asyncio.AbstractServer | None = None

    @property
    def port(self) -> int:
        return self._server.sockets[0].getsockname()[1] if self._server else 0

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._on_client, self._host, 0)
        return self.port

    async def _on_client(self, cr: asyncio.StreamReader, cw: asyncio.StreamWriter) -> None:
        try:
            tr_r, tr_w = await self._transport()
        except Exception:
            cw.close()
            return
        await asyncio.gather(_pump(cr, tr_w), _pump(tr_r, cw))

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None


async def _pump(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
    try:
        while True:
            chunk = await src.read(65536)
            if not chunk:
                break
            dst.write(chunk)
            await dst.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        try:
            dst.close()
        except Exception:
            pass


def direct_transport(host: str, port: int) -> Transport:
    """Transport nối THẲNG tới host:port (dùng cho test cục bộ / cùng LAN thật).
    Bản relay sẽ thay bằng transport WebSocket tới Cloudflare Durable Object."""
    async def _make():
        return await asyncio.open_connection(host, port)
    return _make
