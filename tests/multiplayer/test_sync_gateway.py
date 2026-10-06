"""HTTPS thật: quyền host và lời mời tách biệt; từ chối file sai hash/chuyển hướng."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.room_code import make_room_code, split_room_code
from nostalgia.multiplayer.sync_gateway import HttpRoomSyncGateway, invite_proof
from nostalgia.multiplayer.sync_manifest import manifest_document
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient


def test_paid_upload_and_free_download_use_different_credentials(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
) -> None:
    code = make_room_code()
    room_id, room_secret = split_room_code(code)
    path = f"/v1/rooms/{room_id}/sync"
    payload = b"fixture mod"
    sync_file = SyncFile("mods/example.jar", hashlib.sha256(payload).hexdigest(), len(payload))
    manifest = SyncManifest("Friends", "1.20.1", "forge", "47.4.23", (sync_file,))
    target = tmp_path / sync_file.relative_path
    target.parent.mkdir()
    target.write_bytes(payload)
    server_state.add(path, json.dumps(manifest_document(manifest)).encode())
    server_state.add(path + "/commit", b"{}")
    file_path = path + "/files/" + sync_file.sha256
    server_state.add(file_path, payload)
    host = HttpRoomSyncGateway(server.url(""), http_client, "paid-session")
    host.publish(code, "relay-ticket", SyncSnapshot(manifest, tmp_path))
    body = server_state.received_body(path)
    assert room_secret.encode() not in body
    assert json.loads(body)["invite_proof"] == invite_proof(code)[1]
    assert server_state.received_header(file_path, "Authorization") == "Bearer paid-session"
    assert server_state.received_header(file_path, "X-Room-Host-Ticket") == "relay-ticket"
    guest = HttpRoomSyncGateway(server.url(""), http_client)
    assert guest.resolve(code) == manifest
    assert guest.download(code, sync_file) == payload
    assert server_state.received_header(file_path, "Authorization") == ""
    assert server_state.received_header(file_path, "X-Room-Host-Ticket") == ""
    assert server_state.received_header(file_path, "X-Room-Invite-Proof") == invite_proof(code)[1]


@pytest.mark.parametrize("status", [401, 403, 302, 429, 503])
def test_errors_never_become_a_sync_offer(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    status: int,
) -> None:
    code = make_room_code()
    room_id, _ = split_room_code(code)
    server_state.add(f"/v1/rooms/{room_id}/sync", b"{}", status=status)
    with pytest.raises(MultiplayerError):
        HttpRoomSyncGateway(server.url(""), http_client).resolve(code)


def test_corrupted_download_rejected(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
) -> None:
    code = make_room_code()
    room_id, _ = split_room_code(code)
    sync_file = SyncFile("mods/a.jar", hashlib.sha256(b"good").hexdigest(), 4)
    server_state.add(f"/v1/rooms/{room_id}/sync/files/{sync_file.sha256}", b"evil")
    with pytest.raises(MultiplayerError, match="SHA-256"):
        HttpRoomSyncGateway(server.url(""), http_client).download(code, sync_file)
