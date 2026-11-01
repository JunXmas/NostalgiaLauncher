"""Lỗi làm chết cả một bước mạng phải để lại log warning, không được nuốt im."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, cast

import pytest

from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.room_network import RoomNetwork

if TYPE_CHECKING:
    from nostalgia.multiplayer.host import HostRelay
    from nostalgia.multiplayer.peer_stream import PeerStream


class BrokenStream:
    connection = object()

    async def wait_open(self, **_options: float) -> None:
        raise ConnectionResetError("peer vanished")

    async def close(self) -> None:
        return None


def test_peer_host_stream_failure_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    peer = PeerHost(cast("HostRelay", object()))
    with caplog.at_level(logging.WARNING, "nostalgia.multiplayer.peer_host"):
        asyncio.run(peer._serve(cast("PeerStream", BrokenStream()), "sync", 0.0))
    assert "ConnectionResetError" in caplog.text
    assert "peer vanished" in caplog.text


class CrashedHost:
    async def wait_closed(self) -> None:
        raise OSError("relay socket died")


class Room(RoomNetwork):
    def __init__(self) -> None:
        self.failures: list[str] = []
        self._on_failure = self.failures.append

    async def _teardown(self) -> None:
        return None


def test_relay_host_crash_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    room = Room()
    with caplog.at_level(logging.WARNING, "nostalgia.multiplayer.room_network"):
        asyncio.run(room._watch_host(cast("HostRelay", CrashedHost())))
    assert "relay socket died" in caplog.text
    assert room.failures
