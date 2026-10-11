"""File đi qua nhiều cửa sổ cấp quyền; chỉ thử lại khối mất, không bỏ kiểm hash."""

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import cast

import pytest
from test_peer_transport import Signalling, local_ice

from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.peer_download import PeerDownload
from nostalgia.multiplayer.peer_failure import PeerConnectionError
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.sync_chunk import SYNC_CHUNK_BYTES, read_sync_chunk
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.operations.cancellation import CancelToken


@pytest.mark.parametrize("revoked", [False, True])
def test_file_renews_authorization_and_only_retries_the_missing_chunk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, revoked: bool
) -> None:
    local_ice(monkeypatch)
    content = b"x" * (2 * SYNC_CHUNK_BYTES + 17)
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/custom.jar").write_bytes(content)
    sync_file = SyncFile("mods/custom.jar", hashlib.sha256(content).hexdigest(), len(content))
    offsets: list[int] = []

    def read(snapshot: SyncSnapshot, payload: bytes) -> bytes:
        offsets.append(json.loads(payload)["offset"])
        return read_sync_chunk(snapshot, payload)

    monkeypatch.setattr("nostalgia.multiplayer.peer_host.read_sync_chunk", read)

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 0)
        host.sync_snapshot = SyncSnapshot(
            SyncManifest("Private", "1.20.1", "fabric", "0.16.0", (sync_file,)), tmp_path
        )
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            calls = 0

            def send(self, method: str, url: str, **kwargs: object) -> HttpResponse:
                self.calls += 1
                if self.calls > 1 and revoked:
                    return HttpResponse(403, b"unavailable")
                return signal.send_http(method, url, **kwargs)

        http = Http()
        receiver = PeerDownload(
            "https://signal.test", cast(HttpClient, http), disable_on_failure=False
        )
        chunk = receiver._chunk

        async def expire_after_chunk(*args: object) -> bytes:
            payload = await chunk(*args)  # type: ignore[arg-type]
            receiver._expires = 0
            return payload

        monkeypatch.setattr(receiver, "_chunk", expire_after_chunk)
        try:
            if revoked:
                with pytest.raises(PeerConnectionError, match="quyền đồng bộ"):
                    await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken())
                assert offsets == [0] and http.calls == 2
            else:
                assert (
                    await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken())
                    == content
                )
                assert offsets == [0, SYNC_CHUNK_BYTES, 2 * SYNC_CHUNK_BYTES]
                assert http.calls == 3
        finally:
            await receiver.close()
            await host.close()

    asyncio.run(scenario())


def test_slow_real_dtls_file_keeps_progress_beyond_thirty_seconds(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    local_ice(monkeypatch)
    content = b"z" * (4 * SYNC_CHUNK_BYTES)
    (tmp_path / "resourcepacks").mkdir()
    (tmp_path / "resourcepacks/slow.zip").write_bytes(content)
    sync_file = SyncFile(
        "resourcepacks/slow.zip", hashlib.sha256(content).hexdigest(), len(content)
    )

    def slow_chunk(snapshot: SyncSnapshot, payload: bytes) -> bytes:
        # Chờ có chủ đích: bốn khối vẫn tiến triển nhưng toàn file mất hơn 30 giây.
        time.sleep(8)
        return read_sync_chunk(snapshot, payload)

    monkeypatch.setattr("nostalgia.multiplayer.peer_host.read_sync_chunk", slow_chunk)

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 0)
        host.sync_snapshot = SyncSnapshot(
            SyncManifest("Slow", "1.20.1", "fabric", "0.16.0", (sync_file,)), tmp_path
        )
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        receiver = PeerDownload(
            "https://signal.test", cast(HttpClient, Http()), disable_on_failure=False
        )
        started_at = time.monotonic()
        try:
            assert (
                await asyncio.wait_for(
                    receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken()), 50
                )
                == content
            )
            assert time.monotonic() - started_at > 30
        finally:
            await receiver.close()
            await host.close()

    asyncio.run(scenario())
