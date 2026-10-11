"""DTLS thật vẫn kiểm khối/hash; dữ liệu sai hoặc hủy thao tác không được thử lại."""

import asyncio
import hashlib
from pathlib import Path
from typing import cast

import pytest
from test_peer_transport import Signalling, local_ice

from nostalgia.errors import Cancelled, MultiplayerError
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.peer_download import PeerDownload
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.sync_chunk import SYNC_CHUNK_BYTES, read_sync_chunk
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


@pytest.mark.parametrize("fault", ["id", "length", "hash", "cancel"])
def test_corrupt_or_cancelled_transfer_never_returns_installable_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fault: str
) -> None:
    local_ice(monkeypatch)
    content = b"a" * (2 * SYNC_CHUNK_BYTES + 17)
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/custom.jar").write_bytes(content)
    sync_file = SyncFile("mods/custom.jar", hashlib.sha256(content).hexdigest(), len(content))
    cancel_token = CancelToken()
    reads: list[bool] = []

    def corrupt_chunk(snapshot: SyncSnapshot, payload: bytes) -> bytes:
        reads.append(True)
        reply = read_sync_chunk(snapshot, payload)
        if fault == "id":
            return b"!" + reply[1:]
        if fault == "length":
            return reply[:-1]
        if fault == "hash":
            return reply[:-1] + b"b"
        cancel_token.cancel()
        return reply

    monkeypatch.setattr("nostalgia.multiplayer.peer_host.read_sync_chunk", corrupt_chunk)

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 0)
        host.sync_snapshot = SyncSnapshot(
            SyncManifest("Private", "1.20.1", "fabric", "0.16.0", (sync_file,)), tmp_path
        )
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        receiver = PeerDownload(
            "https://signal.test", cast(HttpClient, Http()), disable_on_failure=False
        )
        try:
            with pytest.raises(Cancelled if fault == "cancel" else MultiplayerError):
                await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, cancel_token)
            assert receiver._stream is None
            assert signal.purposes == ["sync"]
            assert len(reads) == (3 if fault == "hash" else 1)
        finally:
            await receiver.close()
            await host.close()
        assert not host.peer.connections

    asyncio.run(scenario())
