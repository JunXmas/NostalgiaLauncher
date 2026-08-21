"""Cầu nối giữa cơ chế multiplayer (asyncio, `nostalgia.multiplayer`) và Qt.

Codebase không có bridge asyncio/Qt, nên chạy một event loop asyncio riêng trong
một QThread và ra lệnh qua `run_coroutine_threadsafe`; kết quả báo về GUI bằng
Signal (không đụng widget từ thread khác). Mỗi máy chỉ một phiên host HOẶC join.
"""
from __future__ import annotations

import asyncio
import os

from PySide6.QtCore import QThread, Signal

from .. import multiplayer as mp

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # bỏ ký tự dễ nhầm (0/O, 1/I/L)


def make_code(n: int = 6) -> str:
    """Mã phòng ngắn, dễ đọc/chia sẻ; cũng là sessionId của relay."""
    return "".join(_ALPHABET[b % len(_ALPHABET)] for b in os.urandom(n))


class MultiplayerService(QThread):
    # host
    waiting_world = Signal()        # đã bật host, đang chờ "Open to LAN"
    hosting_live = Signal(str)      # (code) world đã bắt được + nối relay xong
    # join
    joined = Signal(int)            # (local_port) cầu sẵn sàng, đã quảng bá LAN
    # chung
    failed = Signal(str)
    ended = Signal()

    def __init__(self, relay: str = mp.DEFAULT_RELAY, parent=None):
        super().__init__(parent)
        self._relay = relay
        self._loop: asyncio.AbstractEventLoop | None = None
        self._objs: list = []           # bridge/host/announcer đang chạy
        self._stopping = False
        self.role: str | None = None    # 'host' | 'join'
        self.code: str | None = None
        self.local_port: int = 0

    # ── vòng đời thread ──────────────────────────────────────────────────────
    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def _ensure(self) -> None:
        if not self.isRunning():
            self.start()
            while self._loop is None:      # chờ loop dựng xong
                self.msleep(5)

    def _submit(self, coro) -> None:
        assert self._loop is not None
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    # ── host ─────────────────────────────────────────────────────────────────
    def host(self, code: str) -> None:
        self._ensure()
        self.role, self.code, self._stopping = "host", code, False
        self._submit(self._host_coro(code))

    async def _host_coro(self, code: str) -> None:
        loop = asyncio.get_event_loop()
        self.waiting_world.emit()
        try:
            while not self._stopping:
                res = await loop.run_in_executor(None, mp.detect_open_to_lan, 4.0)
                if res:
                    break
            else:
                return
            world_port, _motd = res
            hr = mp.HostRelay(self._relay, code, world_port)
            hr.start()
            self._objs.append(hr)
            self.hosting_live.emit(code)
        except Exception as e:                       # noqa: BLE001
            self.failed.emit(str(e))

    # ── join ─────────────────────────────────────────────────────────────────
    def join(self, code: str) -> None:
        self._ensure()
        self.role, self.code, self._stopping = "join", code, False
        self._submit(self._join_coro(code))

    async def _join_coro(self, code: str) -> None:
        try:
            bridge = mp.TcpBridge(mp.ws_transport(self._relay, code))
            port = await bridge.start()
            ann = mp.LanAnnouncer(port)
            ann.start()
            self._objs += [bridge, ann]
            self.local_port = port
            self.joined.emit(port)
        except Exception as e:                       # noqa: BLE001
            self.failed.emit(str(e))

    # ── dừng phiên / tắt ──────────────────────────────────────────────────────
    def stop_session(self) -> None:
        self._stopping = True
        if self._loop and self._loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._stop_objs(), self._loop)
            try:
                fut.result(timeout=5)
            except Exception:                        # noqa: BLE001
                pass
        self.role = self.code = None
        self.local_port = 0
        self.ended.emit()

    async def _stop_objs(self) -> None:
        for o in self._objs:
            try:
                r = o.stop()
                if asyncio.iscoroutine(r):
                    await r
            except Exception:                        # noqa: BLE001
                pass
        self._objs.clear()

    def shutdown(self) -> None:
        try:
            self.stop_session()
        finally:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            self.wait(3000)
