"""Vrais échanges HTTPS en blocs, annulation entre blocs et rejet des données tronquées."""

import hashlib
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.room_code import make_room_code
from nostalgia.multiplayer.sync_chunk import SYNC_CHUNK_BYTES
from nostalgia.multiplayer.sync_gateway import HttpRoomSyncGateway, invite_proof
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


@pytest.mark.parametrize("truncated", [False, True])
def test_relay_download_uses_offsets_and_rejects_partial_chunks(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    truncated: bool,
) -> None:
    code = make_room_code()
    room_id, _proof = invite_proof(code)
    chunk = b"x" * SYNC_CHUNK_BYTES
    payload = chunk * 2
    sync_file = SyncFile("mods/private.jar", hashlib.sha256(payload).hexdigest(), len(payload))
    path = f"/v1/rooms/{room_id}/sync/files/{sync_file.sha256}"
    server_state.add(
        path, chunk[:-1] if truncated else chunk, response_headers=(("X-Sync-Transport", "relay"),)
    )
    guest = HttpRoomSyncGateway(server.url(""), http_client)
    if truncated:
        with pytest.raises(MultiplayerError, match="đầu tiên"):
            guest.download(code, sync_file)
    else:
        assert guest.download(code, sync_file) == payload
        assert server_state.request_count(path) == 2
        assert server_state.routes[path].received_path == path + f"?offset={SYNC_CHUNK_BYTES}"


def test_relay_publish_attaches_snapshot_without_uploading_jar(
    tmp_path: Path,
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
) -> None:
    code = make_room_code()
    room_id, _proof = invite_proof(code)
    path = f"/v1/rooms/{room_id}/sync"
    server_state.add(path, b"{}")
    server_state.add(path + "/commit", b"{}")
    attached: list[SyncSnapshot] = []
    snapshot = SyncSnapshot(SyncManifest("A", "1.20.1", "vanilla", "", ()), tmp_path)
    host = HttpRoomSyncGateway(
        server.url(""), http_client, "session", attach_source=attached.append
    )
    host.publish(code, "ticket", snapshot, cancel_token=CancelToken())
    assert attached == [snapshot]
    assert b'"transport": "relay"' in server_state.received_body(path)
    assert server_state.request_count(path + "/commit") == 1
