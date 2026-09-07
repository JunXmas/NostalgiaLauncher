"""Tầng dịch vụ: một vòng lặp asyncio trong luồng riêng, lệnh gọi từ luồng giao diện.

Mỗi máy chỉ có một phòng tại một thời điểm: đang host HOẶC đang vào. Trạng thái báo ra bằng
`on_status(RoomStatus)`, lỗi bằng `on_failure(str)` — cả hai gọi từ luồng của vòng lặp, người
nhận tự nhảy về luồng của mình. Dừng là dừng hết: task, socket, beacon (luật L10).
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from collections.abc import Callable
from concurrent.futures import Future
from dataclasses import replace

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.lan import LanWorld, announce_forever, detect_open_to_lan
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.room_code import make_room_code, split_room_code
from nostalgia.net.websocket import TlsContext

DetectWorld = Callable[[float], LanWorld | None]
WORLD_POLL_SECONDS = 2.0
WORLD_WAIT_SECONDS = 600.0


class RoomService:
    def __init__(
        self,
        relay_url: str,
        *,
        on_status: Callable[[RoomStatus], None],
        on_failure: Callable[[str], None],
        detect_world: DetectWorld = detect_open_to_lan,
        tls_context: TlsContext | None = None,
    ) -> None:
        self._relay_url = relay_url
        self._on_status = on_status
        self._on_failure = on_failure
        self._detect_world = detect_world
        self._tls_context = tls_context
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="nostalgia-multiplayer", daemon=True
        )
        self._thread.start()
        self._status = RoomStatus()
        self._flow: asyncio.Task[None] | None = None
        self._host: HostRelay | None = None
        self._joiner: JoinerBridge | None = None
        self._beacon: asyncio.Task[None] | None = None

    # ----- lệnh từ luồng giao diện -----

    def start_hosting(self) -> Future[None]:
        return self._submit(self._host_flow())

    def join(self, room_code: str) -> Future[None]:
        return self._submit(self._join_flow(room_code))

    def set_locked(self, locked: bool) -> Future[None]:
        async def apply() -> None:
            if self._host is not None:
                self._host.locked = locked
                self._publish(locked=locked)

        return self._submit(apply())

    def stop(self) -> Future[None]:
        return self._submit(self._teardown())

    def shutdown(self, timeout_seconds: float = 3.0) -> None:
        """Đóng launcher: dừng phòng rồi dừng vòng lặp. Không để luồng mồ côi."""
        with contextlib.suppress(Exception):
            self.stop().result(timeout_seconds)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout_seconds)
        if not self._loop.is_running():
            self._loop.close()

    # ----- luồng của vòng lặp -----

    def _submit(self, coroutine: object) -> Future[None]:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)  # type: ignore[arg-type]

    async def _host_flow(self) -> None:
        await self._teardown()
        room_code = make_room_code()
        room_id, room_secret = split_room_code(room_code)
        self._publish(role="waiting_world", room_code=room_code)
        self._flow = asyncio.current_task()
        try:
            world = await self._wait_for_world()
            host = HostRelay(
                self._relay_url,
                room_id,
                room_secret,
                world.world_port,
                tls_context=self._tls_context,
                on_joiners_changed=lambda count: self._publish(joiner_count=count),
            )
            await host.connect()
            host.start()
            self._host = host
            self._publish(role="hosting", world_name=world.world_name)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await self._teardown()
            self._on_failure(str(exc))

    async def _wait_for_world(self) -> LanWorld:
        deadline = self._loop.time() + WORLD_WAIT_SECONDS
        while self._loop.time() < deadline:
            world = await self._loop.run_in_executor(None, self._detect_world, WORLD_POLL_SECONDS)
            if world is not None:
                return world
        raise MultiplayerError("không thấy world nào mở LAN: vào game, bấm Esc → Open to LAN")

    async def _join_flow(self, room_code: str) -> None:
        await self._teardown()
        try:
            room_id, room_secret = split_room_code(room_code)
            joiner = JoinerBridge(
                self._relay_url, room_id, room_secret, tls_context=self._tls_context
            )
            await joiner.probe()
            local_port = await joiner.start()
            self._joiner = joiner
            self._beacon = self._loop.create_task(
                announce_forever(local_port, "§bNostalgia §7— phòng của bạn")
            )
            self._publish(role="joined", local_port=local_port)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await self._teardown()
            self._on_failure(str(exc))

    async def _teardown(self) -> None:
        flow, self._flow = self._flow, None
        if flow is not None and flow is not asyncio.current_task():
            flow.cancel()
            # Task đã chết vì lỗi thì `await` ném lại lỗi đó; dọn dẹp vẫn phải đi tới cùng.
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await flow
        beacon, self._beacon = self._beacon, None
        if beacon is not None:
            beacon.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await beacon
        joiner, self._joiner = self._joiner, None
        if joiner is not None:
            await joiner.stop()
        host, self._host = self._host, None
        if host is not None:
            await host.stop()
        self._status = RoomStatus()
        self._on_status(self._status)

    def _publish(self, **changes: object) -> None:
        self._status = replace(self._status, **changes)  # type: ignore[arg-type]
        self._on_status(self._status)
