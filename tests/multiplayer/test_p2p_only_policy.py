"""Relay mặc định khóa; không mở WebSocket hoặc HTTP file khi P2P không sẵn sàng."""

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.peer_download import PeerDownload
from nostalgia.multiplayer.room_watch import RoomWatch
from nostalgia.multiplayer.service import RoomService
from nostalgia.multiplayer.sync_gateway import HttpRoomSyncGateway
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.net.http import HttpClient, HttpResponse
from nostalgia.operations.cancellation import CancelToken


class NoDataHttp:
    def send(self, *_args: object, **_kwargs: object) -> None:
        raise AssertionError("Không được tải file qua dịch vụ phòng.")


@pytest.mark.parametrize("disable_on_failure", [False, True])
def test_retry_p2p_after_network_failure_is_not_permanently_disabled(
    monkeypatch: pytest.MonkeyPatch, disable_on_failure: bool
) -> None:
    attempts: list[bool] = []

    async def fail(*_args: object) -> None:
        attempts.append(True)
        raise ConnectionError("Mạng chặn P2P.")

    monkeypatch.setattr("nostalgia.multiplayer.peer_download.connect_peer", fail)

    async def scenario() -> None:
        receiver = PeerDownload(
            "https://signal.test",
            cast(HttpClient, NoDataHttp()),
            disable_on_failure=disable_on_failure,
        )
        sync_file = SyncFile("mods/custom.jar", "a" * 64, 1)
        for _ in range(2):
            assert await receiver.download("ABCDEFABCDEFGHJKMN", sync_file, CancelToken()) is None
        assert len(attempts) == (1 if disable_on_failure else 2)
        await receiver.close()

    asyncio.run(scenario())


def test_p2p_publish_only_sends_manifest_and_commit(tmp_path: Path) -> None:
    requests: list[tuple[str, str, bytes | None]] = []
    attached: list[SyncSnapshot] = []

    class Http:
        def send(self, method: str, url: str, **kwargs: Any) -> HttpResponse:
            requests.append((method, url, kwargs.get("body")))
            return HttpResponse(200, b"{}")

    sync_file = SyncFile("mods/custom.jar", "a" * 64, 12)
    snapshot = SyncSnapshot(
        SyncManifest("P2P", "1.20.1", "fabric", "0.16.0", (sync_file,)), tmp_path
    )
    gateway = HttpRoomSyncGateway(
        "https://signal.test",
        cast(HttpClient, Http()),
        "paid-session",
        attach_source=attached.append,
    )
    gateway.publish("ABCDEFABCDEFGHJKMN", "host-ticket", snapshot)
    assert attached == [snapshot]
    assert [(method, url) for method, url, _ in requests] == [
        ("POST", "https://signal.test/v1/rooms/ABCDEF/sync"),
        ("POST", "https://signal.test/v1/rooms/ABCDEF/sync/commit"),
    ]
    assert json.loads(requests[0][2] or b"")["transport"] == "peer"


@pytest.mark.parametrize("peer_available", [False, True])
def test_custom_file_never_falls_back_to_http(peer_available: bool) -> None:
    payload = b"custom mod"
    sync_file = SyncFile("mods/custom.jar", hashlib.sha256(payload).hexdigest(), len(payload))
    gateway = HttpRoomSyncGateway(
        "https://signal.test",
        cast(HttpClient, NoDataHttp()),
        download_peer=lambda *_args: payload if peer_available else None,
    )
    if peer_available:
        assert gateway.download("ABCDEFABCDEFGHJKMN", sync_file) == payload
    else:
        with pytest.raises(MultiplayerError, match="Relay dữ liệu đã tắt"):
            gateway.download("ABCDEFABCDEFGHJKMN", sync_file)


def test_probe_and_game_connections_cannot_open_relay_without_live_peer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relay_calls: list[bool] = []

    async def forbidden(*_args: object, **_kwargs: object) -> None:
        relay_calls.append(True)
        raise AssertionError("Không được mở socket relay.")

    monkeypatch.setattr("nostalgia.multiplayer.bridge.WebSocketClient.connect", forbidden)

    async def scenario() -> None:
        guest = JoinerBridge("wss://signal.test", "ABCDEF", "ABCDEFGHJKMN")
        try:
            await guest.probe()
            await guest.start()
            reader, writer = await asyncio.open_connection("127.0.0.1", guest.local_port)
            assert await asyncio.wait_for(reader.read(1), 3) == b""
            writer.close()
            await writer.wait_closed()
            assert not relay_calls
        finally:
            await guest.stop()

    asyncio.run(scenario())


@pytest.mark.parametrize("missing", [False, True])
def test_old_or_missing_room_reports_failure_and_never_marks_world_ready(missing: bool) -> None:
    class Http:
        def send(self, *_args: object, **_kwargs: object) -> HttpResponse:
            return (
                HttpResponse(404, b"")
                if missing
                else HttpResponse(
                    200,
                    json.dumps(
                        {
                            "format": 1,
                            "world_ready": True,
                            "direct": False,
                        }
                    ).encode(),
                )
            )

    class Room(RoomWatch):
        def __init__(self) -> None:
            self._room_http = cast(HttpClient, Http())
            self._relay_url = "wss://signal.test"
            self._joiner = cast(Any, SimpleNamespace(peer=None))
            self.states: list[dict[str, object]] = []
            self.failures: list[str] = []
            self._on_failure = self.failures.append

        def _publish(self, **changes: object) -> None:
            self.states.append(changes)

    async def scenario() -> None:
        room = Room()
        await room._watch_guest("ABCDEFABCDEFGHJKMN")
        assert room.failures and room.states[-1] == {
            "connection_kind": "failed",
            "world_ready": False,
        }
        assert all(state.get("world_ready") is not True for state in room.states)

    asyncio.run(scenario())


def test_service_without_p2p_configuration_never_opens_host_relay() -> None:
    failures: list[str] = []
    service = RoomService(
        "wss://signal.test", on_status=lambda _status: None, on_failure=failures.append
    )
    try:
        service.start_hosting().result(3)
        assert failures and "relay dữ liệu đã tắt" in failures[-1]
        assert service._host is None
    finally:
        service.shutdown()
