"""Chỉ mục lớn đi qua DTLS trước khi mở LAN, dùng chung kênh với file custom."""

import asyncio
import hashlib
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from test_peer_transport import Signalling, local_ice

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.peer_download import PeerDownload
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.peer_manifest import read_manifest_chunk
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken


@pytest.mark.parametrize("changed", [False, True])
def test_large_manifest_and_file_use_direct_channel_without_a_world(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, changed: bool
) -> None:
    local_ice(monkeypatch)
    content = b"private mod"
    (tmp_path / "mods").mkdir()
    (tmp_path / "mods/custom.jar").write_bytes(content)
    chosen = SyncFile("mods/custom.jar", hashlib.sha256(content).hexdigest(), len(content))
    manifest = SyncManifest(
        "Friends",
        "1.21.11",
        "fabric",
        "0.19.5",
        (
            chosen,
            *(
                SyncFile(f"config/options-{index}.json", hashlib.sha256(b"").hexdigest(), 0)
                for index in range(1000)
            ),
        ),
    )
    requested = 0

    def send_manifest(snapshot: SyncSnapshot, payload: bytes) -> bytes:
        nonlocal requested
        requested += 1
        if changed and requested > 1:
            snapshot = replace(snapshot, manifest=replace(snapshot.manifest, name="Changed"))
        return read_manifest_chunk(snapshot, payload)

    monkeypatch.setattr("nostalgia.multiplayer.peer_host.read_manifest_chunk", send_manifest)

    async def scenario() -> None:
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", 0)
        host.sync_snapshot = SyncSnapshot(manifest, tmp_path)
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        receiver = PeerDownload(
            "https://signal.test", cast(HttpClient, Http()), disable_on_failure=False
        )
        try:
            if changed:
                with pytest.raises(MultiplayerError, match="đã thay đổi"):
                    await receiver.fetch_manifest("ABCDEFABCDEFGHJKMN", CancelToken())
                assert receiver._stream is None
            else:
                assert (
                    await receiver.fetch_manifest("ABCDEFABCDEFGHJKMN", CancelToken()) == manifest
                )
                assert (
                    await receiver.download("ABCDEFABCDEFGHJKMN", chosen, CancelToken()) == content
                )
            assert requested > 1 and signal.purposes == ["sync"]
        finally:
            await receiver.close()
            await host.close()
        assert not host.peer.connections and not host.peer.routes

    asyncio.run(scenario())
