"""Siêu dữ liệu phòng và P2P; nền relay giữ lại nhưng mặc định khóa dữ liệu."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Callable
from concurrent.futures import Future
from importlib.util import find_spec
from typing import TYPE_CHECKING

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.lan import announce_forever
from nostalgia.multiplayer.mux import ROOM_META, pack_mux_frame
from nostalgia.multiplayer.room_code import split_room_code
from nostalgia.multiplayer.room_watch import RoomWatch
from nostalgia.multiplayer.sync_gateway import invite_proof
from nostalgia.multiplayer.sync_model import SyncSnapshot
from nostalgia.net.http import HttpClient
from nostalgia.net.websocket import TlsContext

if TYPE_CHECKING:
    from nostalgia.multiplayer.host import HostRelay
    from nostalgia.multiplayer.model import RoomStatus
    from nostalgia.multiplayer.peer_download import PeerDownload
    from nostalgia.multiplayer.sync_model import SyncFile
    from nostalgia.operations.cancellation import CancelToken


class RoomNetwork(RoomWatch):
    _owns_http: bool
    _host: HostRelay | None
    _joiner: JoinerBridge | None
    _status: RoomStatus
    _loop: asyncio.AbstractEventLoop
    _relay_url: str
    _on_failure: Callable[[str], None]
    _tls_context: TlsContext | None
    _flow: asyncio.Task[None] | None
    _beacon: asyncio.Task[None] | None

    def _publish(self, **changes: object) -> None: ...
    def _submit(self, coroutine: object) -> Future[None]:
        raise NotImplementedError

    def set_locked(self, locked: bool) -> Future[None]:
        async def apply() -> None:
            if self._host is not None:
                self._host.locked = locked
                self._publish(locked=locked)
                await self.publish_room_metadata()

        return self._submit(apply())

    def download_file(
        self, room_code: str, sync_file: SyncFile, cancel_token: CancelToken
    ) -> Future[bytes | None]:
        return asyncio.run_coroutine_threadsafe(
            self.download_peer_file(room_code, sync_file, cancel_token), self._loop
        )

    def set_sync_snapshot(self, snapshot: SyncSnapshot) -> Future[None]:
        async def apply() -> None:
            if self._host is None or self._status.role not in ("hosting", "waiting_world"):
                raise MultiplayerError("Phòng host không còn hoạt động.")
            self._host.sync_snapshot = snapshot

        return self._submit(apply())

    async def _teardown(self) -> None:
        raise NotImplementedError

    async def _watch_host(self, host: HostRelay) -> None:
        try:
            await host.wait_closed()
        except asyncio.CancelledError:
            return
        except Exception:
            pass
        await self._teardown()
        self._on_failure("Mất kết nối relay. Hãy mở lại phòng; game LAN vẫn còn trên máy bạn.")

    def initialize_network(self, http_client: HttpClient | None) -> None:
        self._room_http = http_client
        self._direct_allowed = True
        self._relay_enabled = False
        self._network_task: asyncio.Task[None] | None = None
        self._room_label = "Minecraft"
        self._sharing = False
        self._peer_download: PeerDownload | None = None

    def require_room_transport(self) -> None:
        if not self._relay_enabled and (
            not self._direct_allowed
            or find_spec("aiortc") is None
            or self._room_http is None
            or not self._relay_url.startswith("wss://")
        ):
            raise MultiplayerError(
                "Không thể dùng P2P. Hãy cập nhật launcher và kiểm tra cấu hình phòng; "
                "relay dữ liệu đã tắt."
            )

    def set_direct_allowed(self, allowed: bool) -> None:
        if self._status.role == "idle":
            self._direct_allowed = allowed

    def prepare_room(self, room_name: str, sharing: bool) -> None:
        if self._status.role == "idle":
            self._room_label, self._sharing = room_name[:120], sharing

    async def publish_room_metadata(self) -> None:
        host = self._host
        if host is None or host._socket is None:
            return
        _, proof = invite_proof(self._status.room_code)
        await host._socket.send(
            pack_mux_frame(
                0,
                ROOM_META,
                json.dumps(
                    {
                        "proof": proof,
                        "name": self._room_label,
                        "ready": host.world_port > 0,
                        "direct": host.peer is not None,
                        "sharing": self._sharing,
                        "locked": host.locked,
                    }
                ).encode(),
            )
        )

    def enable_direct_host(self) -> None:
        if not self._direct_allowed or self._host is None or find_spec("aiortc") is None:
            return
        try:
            from nostalgia.multiplayer.peer_host import PeerHost

            self._host.peer = PeerHost(self._host)
        except ImportError:
            pass

    async def close_room_network(self) -> None:
        task, self._network_task = self._network_task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self._peer_download is not None:
            await self._peer_download.close()
            self._peer_download = None

    async def download_peer_file(
        self, room_code: str, sync_file: SyncFile, cancel_token: CancelToken
    ) -> bytes | None:
        if not self._direct_allowed or self._joiner is None or self._room_http is None:
            return self.unavailable_peer_file()
        if not self._relay_url.startswith("wss://"):
            return self.unavailable_peer_file()
        try:
            from nostalgia.multiplayer.peer_download import PeerDownload
        except ImportError:
            return self.unavailable_peer_file()
        if self._peer_download is None:
            base_url = "https://" + self._relay_url.removeprefix("wss://").rstrip("/")
            self._peer_download = PeerDownload(
                base_url, self._room_http, disable_on_failure=self._relay_enabled
            )
        payload = await self._peer_download.download(room_code, sync_file, cancel_token)
        return payload if payload is not None else self.unavailable_peer_file()

    def unavailable_peer_file(self) -> bytes | None:
        if not self._relay_enabled:
            raise MultiplayerError(
                "Không thể đồng bộ file qua P2P. Relay dữ liệu đã tắt; "
                "hãy kiểm tra mạng và thử lại."
            )
        return None

    def close_room_http(self) -> None:
        if self._owns_http and self._room_http is not None:
            self._room_http.close()

    async def _join_flow(self, room_code: str) -> None:
        await self._teardown()
        self._flow = asyncio.current_task()
        try:
            self.require_room_transport()
            room_id, room_secret = split_room_code(room_code)
            joiner = JoinerBridge(
                self._relay_url,
                room_id,
                room_secret,
                tls_context=self._tls_context,
                relay_enabled=self._relay_enabled,
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
                connection_kind="pending" if not self._relay_enabled else "relay",
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
