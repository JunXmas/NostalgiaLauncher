"""Phòng có thể nhận khách trước LAN; relay chết không được để UI chờ mãi."""

import pytest
from test_end_to_end import game_client
from test_service import LoopThread, wait_for
from test_service import remote as remote

from nostalgia.multiplayer.lan import LanWorld
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService


def test_guest_enters_lobby_before_game_and_same_room_becomes_playable(
    remote: LoopThread, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "nostalgia.multiplayer.service.probe_lan_port", lambda port: LanWorld(port, "Chosen world")
    )
    host_updates: list[RoomStatus] = []
    guest_updates: list[RoomStatus] = []
    errors: list[str] = []
    host = RoomService(
        remote.relay.url,
        on_status=host_updates.append,
        on_failure=errors.append,
        relay_enabled=True,
    )
    guest = RoomService(
        remote.relay.url,
        on_status=guest_updates.append,
        on_failure=errors.append,
        relay_enabled=True,
    )
    host.prepare_room("Chosen pack", False)
    try:
        hosting = host.start_hosting(auto_detect=False)
        wait_for(lambda: bool(host_updates) and host_updates[-1].role == "waiting_world")
        room_code = host_updates[-1].room_code
        assert not host_updates[-1].world_ready and not hosting.done()
        guest.join(room_code).result(5)
        assert guest_updates[-1].role == "joined"
        assert remote.run(game_client(guest_updates[-1].local_port)) == b""
        host.supply_lan_port(remote.world.port).result(5)
        hosting.result(5)
        assert host_updates[-1].room_code == room_code
        assert remote.run(game_client(guest_updates[-1].local_port))
        assert not errors
    finally:
        host.shutdown()
        guest.shutdown()


def test_relay_disconnect_while_waiting_lan_releases_room_immediately(remote: LoopThread) -> None:
    updates: list[RoomStatus] = []
    errors: list[str] = []
    host = RoomService(
        remote.relay.url, on_status=updates.append, on_failure=errors.append, relay_enabled=True
    )
    try:
        hosting = host.start_hosting(auto_detect=False)
        wait_for(lambda: bool(updates) and updates[-1].role == "waiting_world")
        remote.run(remote.relay.stop())
        wait_for(lambda: bool(errors))
        assert updates[-1].role == "idle" and hosting.done()
    finally:
        host.shutdown()
