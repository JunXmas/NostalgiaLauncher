"""Khách đợi host chuẩn bị xong; không tiêu mất lượt thương lượng P2P khi phòng khóa."""

import asyncio
import json
from types import SimpleNamespace
from typing import cast

import pytest

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.room_watch import RoomWatch
from nostalgia.net.http import HttpClient, HttpResponse


def test_guest_waits_for_unlock_before_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[bool] = []
    delays: list[float] = []
    states: list[dict[str, object]] = []

    class Http:
        def send(self, *_args: object, **_kwargs: object) -> HttpResponse:
            requests.append(True)
            return HttpResponse(
                200,
                json.dumps(
                    {"format": 1, "world_ready": True, "direct": True, "locked": len(requests) == 1}
                ).encode(),
            )

    class Room(RoomWatch):
        def __init__(self) -> None:
            self._relay_url = "wss://signal.test"
            self._room_http = cast(HttpClient, Http())
            self._joiner = cast(JoinerBridge, SimpleNamespace(peer=None))
            self._direct_allowed = True
            self._relay_enabled = False
            self.connections = 0
            self.failures: list[str] = []
            self._on_failure = self.failures.append

        def _publish(self, **changes: object) -> None:
            states.append(changes)

        async def _connect_game_peer(self, *_args: object) -> bool:
            assert len(requests) == 2, "host vẫn khóa; thương lượng lúc này sẽ bị từ chối"
            self.connections += 1
            assert self._joiner is not None
            self._joiner.peer = SimpleNamespace(closed=False)  # type: ignore[assignment]
            return True

    async def scenario() -> None:
        room = Room()

        async def sleep(delay: float) -> None:
            delays.append(delay)
            if len(requests) == 2:
                room._joiner = None

        monkeypatch.setattr("nostalgia.multiplayer.room_watch.asyncio.sleep", sleep)
        await room._watch_guest("ABCDEFABCDEFGHJKMN")
        assert room.connections == 1 and not room.failures
        assert states[0]["locked"] is True and states[0]["world_ready"] is False
        assert delays == [15, 60]

    asyncio.run(scenario())
