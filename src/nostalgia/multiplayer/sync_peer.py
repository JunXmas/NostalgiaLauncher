"""Gateway miễn phí: chỉ mục và file lấy trực tiếp từ chủ phòng đã xác thực."""

from collections.abc import Callable

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.room_code import split_room_code
from nostalgia.multiplayer.sync_direct import fetch_peer_file
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.operations.cancellation import CancelToken


class PeerRoomSyncGateway:
    requires_live_source = True

    def __init__(
        self,
        publish_snapshot: Callable[[str, str, SyncSnapshot], None],
        fetch_manifest: Callable[[str], SyncManifest | None],
        download_peer: Callable[[str, SyncFile, CancelToken], bytes | None],
    ) -> None:
        self._publish_snapshot = publish_snapshot
        self._fetch_manifest = fetch_manifest
        self._download_peer = download_peer

    def publish(
        self,
        room_code: str,
        host_ticket: str,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken | None = None,
    ) -> None:
        split_room_code(room_code)
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        self._publish_snapshot(room_code, host_ticket, snapshot)

    def resolve(self, room_code: str) -> SyncManifest | None:
        split_room_code(room_code)
        return self._fetch_manifest(room_code)

    def download(
        self, room_code: str, sync_file: SyncFile, *, cancel_token: CancelToken | None = None
    ) -> bytes:
        payload = fetch_peer_file(self._download_peer, room_code, sync_file, cancel_token)
        if payload is None:
            raise MultiplayerError("Không lấy được file trực tiếp từ chủ phòng. Hãy thử lại.")
        return payload

    def download_cancelable(
        self, room_code: str, sync_file: SyncFile, cancel_token: CancelToken
    ) -> bytes:
        return self.download(room_code, sync_file, cancel_token=cancel_token)
