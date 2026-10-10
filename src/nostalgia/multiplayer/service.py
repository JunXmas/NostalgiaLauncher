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
from nostalgia.multiplayer.lan_probe import probe_lan_port
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.room_code import make_room_code, split_room_code
from nostalgia.multiplayer.room_network import RoomNetwork
from nostalgia.net.http import HttpClient
from nostalgia.net.websocket import TlsContext

DetectWorld = Callable[[float], LanWorld | None]
WORLD_POLL_SECONDS = 2.0
WORLD_WAIT_SECONDS = 3600.0


class RoomService(RoomNetwork):
    def __init__(
        self,
        relay_url: str,
        *,
        on_status: Callable[[RoomStatus], None],
        on_failure: Callable[[str], None],
        detect_world: DetectWorld = detect_open_to_lan,
        tls_context: TlsContext | None = None,
        http_client: HttpClient | None = None,
        owns_http: bool = False,
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
        self._manual_port = 0
        self.initialize_network(http_client)
        self._owns_http = owns_http

    # ----- lệnh từ luồng giao diện -----

    def start_hosting(self, *, auto_detect: bool = True) -> Future[None]:
        return self._submit(self._host_flow(auto_detect=auto_detect))

    def join(self, room_code: str) -> Future[None]:
        return self._submit(self._join_flow(room_code))

    def supply_lan_port(self, world_port: int) -> Future[None]:
        async def apply() -> None:
            if self._status.role == "waiting_world":
                self._manual_port = world_port

        return self._submit(apply())

    def stop(self) -> Future[None]:
        return self._submit(self._teardown())

    def shutdown(self, timeout_seconds: float = 3.0) -> None:
        """Đóng launcher: dừng phòng rồi dừng vòng lặp. Không để luồng mồ côi."""
        if self._loop.is_closed():
            return
        with contextlib.suppress(Exception):
            self.stop().result(timeout_seconds)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout_seconds)
        if not self._loop.is_running():
            self._loop.close()
        self.close_room_http()

    # ----- luồng của vòng lặp -----

    def _submit(self, coroutine: object) -> Future[None]:
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop)  # type: ignore[arg-type]

    async def _host_flow(self, *, auto_detect: bool = True) -> None:
        await self._teardown()
        room_code = make_room_code()
        room_id, room_secret = split_room_code(room_code)
        self._flow = asyncio.current_task()
        try:
            host = HostRelay(
                self._relay_url,
                room_id,
                room_secret,
                0,
                tls_context=self._tls_context,
                on_joiners_changed=lambda count: self._publish(joiner_count=count),
            )
            await host.connect()
            host.start()
            self._host = host
            self._publish(
                role="waiting_world",
                room_code=room_code,
                world_ready=False,
                world_name=self._room_label,
                host_ticket=host.sync_ticket,
            )
            self.enable_direct_host()
            await self.publish_room_metadata()
            waiting = asyncio.create_task(self._wait_for_world(auto_detect=auto_detect))
            try:
                assert host._runner is not None
                await asyncio.wait((waiting, host._runner), return_when=asyncio.FIRST_COMPLETED)
                if not waiting.done():
                    raise MultiplayerError("Phòng đã đóng trong lúc chờ world.")
                world = waiting.result()
            finally:
                waiting.cancel()
                with contextlib.suppress(Exception, asyncio.CancelledError):
                    await waiting
            if self._host is not host or host._runner is None or host._runner.done():
                raise MultiplayerError("Phòng đã đóng trong lúc chờ world.")
            host.set_world_port(world.world_port)
            await self.publish_room_metadata()
            self._publish(role="hosting", world_name=world.world_name, world_ready=True)
            self._flow = self._loop.create_task(self._watch_host(host))
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await self._teardown()
            self._on_failure(str(exc))

    async def _wait_for_world(self, *, auto_detect: bool = True) -> LanWorld:
        deadline = self._loop.time() + WORLD_WAIT_SECONDS
        detector_available = auto_detect
        while self._loop.time() < deadline:
            if self._manual_port:
                world_port, self._manual_port = self._manual_port, 0
                try:
                    return await self._loop.run_in_executor(None, probe_lan_port, world_port)
                except MultiplayerError as exc:
                    self._on_failure(str(exc))
            if not detector_available:
                await asyncio.sleep(0.2)
                continue
            try:
                world = await self._loop.run_in_executor(
                    None, self._detect_world, WORLD_POLL_SECONDS
                )
            except MultiplayerError:
                detector_available = False
                self._on_failure(
                    "Không dò LAN tự động được. Hãy nhập cổng Minecraft báo sau khi mở LAN."
                )
                continue
            if world is not None:
                return world
        raise MultiplayerError("không thấy world nào mở LAN: vào game, bấm Esc → Open to LAN")

    async def _join_flow(self, room_code: str) -> None:
        await self._teardown()
        self._flow = asyncio.current_task()
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
            self._publish(
                role="joined",
                local_port=local_port,
                world_ready=not (
                    self._room_http is not None and self._relay_url.startswith("wss://")
                ),
            )
            self.watch_guest_room(room_code)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            await self._teardown()
            self._on_failure(str(exc))

    async def _teardown(self) -> None:
        await self.close_room_network()
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
        self._manual_port = 0
        self._status = RoomStatus()
        self._on_status(self._status)

    def _publish(self, **changes: object) -> None:
        self._status = replace(self._status, **changes)  # type: ignore[arg-type]
        self._on_status(self._status)
