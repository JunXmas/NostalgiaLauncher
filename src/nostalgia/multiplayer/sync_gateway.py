"""API đồng bộ của relay: host cần phiên Plus + vé host, khách chỉ cần mã phòng."""

from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urlsplit

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.room_code import split_room_code
from nostalgia.multiplayer.sync_manifest import manifest_document, parse_sync_manifest
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient
from nostalgia.net.payload import decode_json
from nostalgia.operations.cancellation import CancelToken


def invite_proof(room_code: str) -> tuple[str, str]:
    room_id, room_secret = split_room_code(room_code)
    proof = hmac.new(
        room_secret.encode(), b"nostalgia-sync-v1:" + room_id.encode(), hashlib.sha256
    ).hexdigest()
    return room_id, proof


class HttpRoomSyncGateway:
    def __init__(self, base_url: str, http_client: HttpClient, session_token: str = "") -> None:
        parts = urlsplit(base_url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
            or any(char.isspace() for char in session_token)
        ):
            raise MultiplayerError("Cấu hình dịch vụ đồng bộ không hợp lệ.")
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client
        self._session_token = session_token

    def publish(
        self,
        room_code: str,
        host_ticket: str,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken | None = None,
    ) -> None:
        if (
            not self._session_token
            or not host_ticket
            or len(host_ticket) > 2048
            or any(char.isspace() for char in host_ticket)
        ):
            raise MultiplayerError(
                "Cần đăng nhập Plus và relay hỗ trợ xác thực chủ phòng trước khi chia sẻ."
            )
        room_id, proof = invite_proof(room_code)
        path = f"/v1/rooms/{room_id}/sync"
        headers = {
            "Authorization": "Bearer " + self._session_token,
            "X-Room-Host-Ticket": host_ticket,
        }
        body = json.dumps(
            {"invite_proof": proof, "manifest": manifest_document(snapshot.manifest)}
        ).encode()
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        self._request("POST", path, {**headers, "Content-Type": "application/json"}, body=body)
        for sync_file in snapshot.manifest.files:
            if cancel_token is not None:
                cancel_token.raise_if_cancelled()
            payload = (snapshot.folder / sync_file.relative_path).read_bytes()
            if (
                len(payload) != sync_file.size
                or hashlib.sha256(payload).hexdigest() != sync_file.sha256
            ):
                raise MultiplayerError(
                    "Modpack đã thay đổi trong lúc chia sẻ. Hãy tạo lại ảnh chụp."
                )
            self._request("PUT", path + "/files/" + sync_file.sha256, headers, body=payload)
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        self._request("POST", path + "/commit", headers)

    def resolve(self, room_code: str) -> SyncManifest | None:
        room_id, proof = invite_proof(room_code)
        payload = self._request(
            "GET", f"/v1/rooms/{room_id}/sync", {"X-Room-Invite-Proof": proof}, absent_ok=True
        )
        return (
            None
            if payload is None
            else parse_sync_manifest(decode_json(payload, what="modpack của phòng"))
        )

    def download(self, room_code: str, sync_file: SyncFile) -> bytes:
        room_id, proof = invite_proof(room_code)
        payload = self._request(
            "GET",
            f"/v1/rooms/{room_id}/sync/files/{sync_file.sha256}",
            {"X-Room-Invite-Proof": proof},
            max_bytes=sync_file.size,
        )
        if (
            payload is None
            or len(payload) != sync_file.size
            or hashlib.sha256(payload).hexdigest() != sync_file.sha256
        ):
            raise MultiplayerError("File đồng bộ không khớp SHA-256; bản chơi chưa được đăng ký.")
        return payload

    def _request(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        *,
        body: bytes | None = None,
        max_bytes: int = 256_000,
        absent_ok: bool = False,
    ) -> bytes | None:
        response = self._http_client.send(
            method, self._base_url + path, headers=headers, body=body, max_bytes=max_bytes
        )
        if absent_ok and response.status == 404:
            return None
        if response.status in (401, 403):
            raise MultiplayerError(
                "Máy chủ từ chối: phiên Plus hoặc quyền chủ phòng không còn hợp lệ."
            )
        if not response.is_ok:
            raise MultiplayerError("Dịch vụ đồng bộ chưa sẵn sàng hoặc phòng đã đóng. Hãy thử lại.")
        return response.body
