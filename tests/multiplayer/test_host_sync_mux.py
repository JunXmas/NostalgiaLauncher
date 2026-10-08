"""Socket host réel: les chunks privés passent sur stream 0 sans ouvrir le world."""

import asyncio
import json
from pathlib import Path

from fake_relay import FakeRelay, Room, ServerSocket

from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.mux import SYNC_DATA, SYNC_REQUEST, pack_mux_frame, unpack_mux_frame
from nostalgia.multiplayer.sync_snapshot import capture_sync_snapshot
from nostalgia.operations.cancellation import CancelToken


class SnapshotRelay(FakeRelay):
    def __init__(self) -> None:
        super().__init__()
        self.responses: asyncio.Queue[bytes] = asyncio.Queue()

    async def _run_host(self, room: Room, host: ServerSocket) -> None:
        room.host = host
        try:
            while payload := await host.receive():
                self.responses.put_nowait(payload)
        finally:
            room.host = None


def test_host_receives_sync_request_and_returns_only_snapshot_bytes(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "mods").mkdir(parents=True)
    (source / "mods/private.jar").write_bytes(b"private exact bytes")
    snapshot = capture_sync_snapshot(
        source,
        tmp_path / "snapshot",
        name="A",
        game_version="1.20.1",
        loader_kind="vanilla",
        loader_version="",
        cancel_token=CancelToken(),
    )

    async def scenario() -> None:
        relay = SnapshotRelay()
        await relay.start()
        host = HostRelay(relay.url, "ABCDEF", "secret", 51234)
        try:
            await host.connect()
            host.sync_snapshot = snapshot
            host.start()
            request = json.dumps(
                {
                    "request_id": "a" * 32,
                    "sha256": snapshot.manifest.files[0].sha256,
                    "offset": 0,
                    "length": snapshot.manifest.files[0].size,
                }
            ).encode()
            socket = relay.rooms["ABCDEF"].host
            assert socket is not None
            await socket.send(pack_mux_frame(0, SYNC_REQUEST, request))
            response = await asyncio.wait_for(relay.responses.get(), 3)
            assert unpack_mux_frame(response) == (0, SYNC_DATA, b"a" * 32 + b"private exact bytes")
            assert host.joiner_count == 0 and not host._gates
        finally:
            await host.stop()
            await relay.stop()
        assert host.sync_snapshot is None

    asyncio.run(scenario())
