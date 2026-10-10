"""Siêu dữ liệu phòng và đường trực tiếp; relay cũ vẫn dùng được khi thiếu API mới."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Callable
from concurrent.futures import Future
from importlib.util import find_spec
from typing import TYPE_CHECKING

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.mux import ROOM_META, pack_mux_frame
from nostalgia.multiplayer.room_watch import RoomWatch
from nostalgia.multiplayer.sync_gateway import invite_proof
from nostalgia.multiplayer.sync_model import SyncSnapshot
from nostalgia.net.http import HttpClient

if TYPE_CHECKING:
    from nostalgia.multiplayer.bridge import JoinerBridge
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
        self._network_task: asyncio.Task[None] | None = None
        self._room_label = "Minecraft"
        self._sharing = False
        self._peer_download: PeerDownload | None = None

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
            return None
        if not self._relay_url.startswith("wss://"):
            return None
        try:
            from nostalgia.multiplayer.peer_download import PeerDownload
        except ImportError:
            return None
        if self._peer_download is None:
            base_url = "https://" + self._relay_url.removeprefix("wss://").rstrip("/")
            self._peer_download = PeerDownload(base_url, self._room_http)
        return await self._peer_download.download(room_code, sync_file, cancel_token)

    def close_room_http(self) -> None:
        if self._owns_http and self._room_http is not None:
            self._room_http.close()
