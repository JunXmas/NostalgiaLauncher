"""Trao đổi chỉ mục và file qua P2P trên vòng lặp của phòng."""

from __future__ import annotations

import asyncio
import json
from concurrent.futures import Future
from typing import TYPE_CHECKING

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.peer_download import PeerDownload
from nostalgia.multiplayer.room_recovery import RoomRecovery
from nostalgia.multiplayer.sync_gateway import invite_proof
from nostalgia.multiplayer.sync_model import SyncManifest, SyncSnapshot

if TYPE_CHECKING:
    from nostalgia.multiplayer.host import HostRelay
    from nostalgia.multiplayer.sync_model import SyncFile
    from nostalgia.operations.cancellation import CancelToken


class RoomTransfer(RoomRecovery):
    _host: HostRelay | None
    _loop: asyncio.AbstractEventLoop
    _peer_download: PeerDownload | None

    def download_file(
        self, room_code: str, sync_file: SyncFile, cancel_token: CancelToken
    ) -> Future[bytes | None]:
        return asyncio.run_coroutine_threadsafe(
            self.download_peer_file(room_code, sync_file, cancel_token), self._loop
        )

    def set_sync_snapshot(
        self, snapshot: SyncSnapshot, room_code: str = "", host_ticket: str = ""
    ) -> Future[None]:
        async def apply() -> None:
            if self._host is None or self._status.role not in ("hosting", "waiting_world"):
                raise MultiplayerError("Phòng host không còn hoạt động.")
            if room_code and (
                self._status.room_code != room_code or self._status.host_ticket != host_ticket
            ):
                raise MultiplayerError("Phòng chủ đã thay đổi; hãy mở lại chia sẻ.")
            self._host.sync_snapshot = snapshot
            await self.publish_room_metadata()

        return self._submit(apply())

    async def publish_room_metadata(self) -> None:
        raise NotImplementedError

    def fetch_sync_manifest(self, room_code: str) -> Future[SyncManifest | None]:
        return asyncio.run_coroutine_threadsafe(self._fetch_sync_manifest(room_code), self._loop)

    async def _fetch_sync_manifest(self, room_code: str) -> SyncManifest | None:
        from nostalgia.operations.cancellation import CancelToken

        if self._joiner is None or room_code != self._guest_room_code or self._room_http is None:
            return None
        room_id, proof = invite_proof(room_code)
        base_url = "https://" + self._relay_url.removeprefix("wss://").rstrip("/")
        response = await asyncio.to_thread(
            self._room_http.send,
            "GET",
            base_url + f"/v1/rooms/{room_id}/lobby",
            headers={"X-Room-Invite-Proof": proof},
            max_bytes=8192,
        )
        if not response.is_ok:
            raise MultiplayerError("Không đọc được trạng thái chia sẻ của phòng.")
        document = json.loads(response.body)
        if not document.get("sync_ready") or document.get("locked"):
            return None
        if self._peer_download is None:
            self._peer_download = PeerDownload(base_url, self._room_http, disable_on_failure=False)
        return await self._peer_download.fetch_manifest(room_code, CancelToken())

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
