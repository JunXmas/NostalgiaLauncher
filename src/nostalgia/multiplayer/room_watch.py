"""Khách theo dõi phòng chờ nhẹ; nối trực tiếp một lần khi host mở world."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nostalgia.errors import MultiplayerError, NetworkError
from nostalgia.multiplayer.sync_gateway import invite_proof
from nostalgia.net.http import HttpClient

if TYPE_CHECKING:
    from nostalgia.multiplayer.bridge import JoinerBridge


class RoomWatch:
    _joiner: JoinerBridge | None
    _room_http: HttpClient | None
    _relay_url: str
    _direct_allowed: bool
    _on_failure: Callable[[str], None]
    _network_task: asyncio.Task[None] | None

    def _publish(self, **changes: object) -> None: ...

    def watch_guest_room(self, room_code: str) -> None:
        if self._room_http is not None and self._relay_url.startswith("wss://"):
            self._network_task = asyncio.create_task(self._watch_guest(room_code))

    async def _watch_guest(self, room_code: str) -> None:
        room_id, proof = invite_proof(room_code)
        base_url = "https://" + self._relay_url.removeprefix("wss://").rstrip("/")
        known = False
        attempted = False
        http = self._room_http
        assert http is not None
        while self._joiner is not None:
            try:
                response = await asyncio.to_thread(
                    http.send,
                    "GET",
                    base_url + f"/v1/rooms/{room_id}/lobby",
                    headers={"X-Room-Invite-Proof": proof},
                    max_bytes=8192,
                )
                if response.status == 404:
                    if known:
                        self._publish(world_ready=False)
                        self._on_failure("Phòng đã đóng. Hãy rời phòng và nhận lời mời mới.")
                    else:
                        self._publish(world_ready=True)
                    return
                if not response.is_ok:
                    await asyncio.sleep(15)
                    continue
                document: Any = json.loads(response.body)
                if not isinstance(document, dict):
                    raise ValueError("invalid lobby")
                if document.get("format") != 1 or type(document.get("world_ready")) is not bool:
                    return
                known = True
                self._publish(
                    world_ready=document["world_ready"],
                    world_name=str(document.get("name", ""))[:120],
                    share_state="pending" if document.get("sharing") is True else "none",
                )
                if (
                    document["world_ready"]
                    and document.get("direct") is True
                    and self._direct_allowed
                    and not attempted
                ):
                    attempted = True
                    if not await self._connect_game_peer(base_url, room_code, http):
                        return
                if self._joiner.peer is not None and self._joiner.peer.closed:
                    self._publish(connection_kind="relay")
                await asyncio.sleep(60 if document["world_ready"] else 15)
            except asyncio.CancelledError:
                raise
            except (NetworkError, ValueError, KeyError):
                await asyncio.sleep(15)

    async def _connect_game_peer(self, base_url: str, room_code: str, http: HttpClient) -> bool:
        try:
            from nostalgia.multiplayer.peer_connection import connect_peer
            from nostalgia.multiplayer.peer_mux import PeerMux

            self._publish(connection_kind="connecting")
            stream = await connect_peer(base_url, room_code, "game", http)
            if self._joiner is None:
                await stream.close()
                return True
            self._joiner.peer = PeerMux(stream)
            self._publish(connection_kind="direct")
        except (ImportError, ConnectionError, TimeoutError, NetworkError):
            self._publish(connection_kind="relay")
        except MultiplayerError as exc:
            self._publish(connection_kind="relay", world_ready=False)
            self._on_failure(str(exc))
            return False
        return True
