"""Khách theo dõi phòng chờ nhẹ; nối trực tiếp một lần khi host mở world."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from nostalgia.errors import MultiplayerError, NetworkError
from nostalgia.multiplayer.peer_failure import PeerConnectionError
from nostalgia.multiplayer.sync_gateway import invite_proof
from nostalgia.net.http import HttpClient

if TYPE_CHECKING:
    from nostalgia.multiplayer.bridge import JoinerBridge
    from nostalgia.multiplayer.peer_mux import PeerMux


class RoomWatch:
    _joiner: JoinerBridge | None
    _room_http: HttpClient | None
    _relay_url: str
    _direct_allowed: bool
    _relay_enabled: bool = False
    _on_failure: Callable[[str], None]
    _network_task: asyncio.Task[None] | None
    _guest_room_code: str

    def _publish(self, **changes: object) -> None: ...

    def watch_guest_room(self, room_code: str) -> None:
        if self._room_http is not None and self._relay_url.startswith("wss://"):
            self._guest_room_code = room_code
            self._network_task = asyncio.create_task(self._watch_guest(room_code))

    async def _watch_guest(self, room_code: str) -> None:
        room_id, proof = invite_proof(room_code)
        base_url = "https://" + self._relay_url.removeprefix("wss://").rstrip("/")
        known = False
        attempted = False
        failures = 0
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
                    self._publish(world_available=False, lobby_verified=False)
                    if not self._relay_enabled:
                        self.peer_unavailable(
                            "Phòng không hỗ trợ P2P hoặc đã đóng. "
                            "Nhờ host cập nhật launcher và mở lại phòng.",
                            retryable=False,
                        )
                    elif known:
                        self._publish(world_ready=False)
                        self._on_failure("Phòng đã đóng. Hãy rời phòng và nhận lời mời mới.")
                    else:
                        self._publish(world_ready=True)
                    return
                if not response.is_ok:
                    failures += 1
                    if not await self._retry_lobby(failures):
                        return
                    continue
                document: Any = json.loads(response.body)
                if not isinstance(document, dict):
                    raise ValueError("invalid lobby")
                if document.get("format") != 1 or type(document.get("world_ready")) is not bool:
                    self.peer_unavailable(
                        "Thông tin phòng không hợp lệ. Nhờ host cập nhật launcher và mở lại phòng.",
                        retryable=False,
                    )
                    return
                failures = 0
                known = True
                locked = document.get("locked") is True
                self._publish(
                    world_ready=document["world_ready"]
                    and not locked
                    and (
                        self._relay_enabled
                        or (self._joiner.peer is not None and not self._joiner.peer.closed)
                    ),
                    world_name=str(document.get("name", ""))[:120],
                    locked=locked,
                    share_state="pending" if document.get("sharing") is True else "none",
                    world_available=document["world_ready"],
                    lobby_verified=True,
                    connection_note="",
                )
                if (
                    document["world_ready"]
                    and document.get("direct") is not True
                    and not self._relay_enabled
                ):
                    self.peer_unavailable(
                        "Host chưa hỗ trợ P2P. Nhờ host cập nhật launcher; relay dữ liệu đã tắt.",
                        retryable=False,
                    )
                    return
                if (
                    document["world_ready"]
                    and document.get("direct") is True
                    and self._direct_allowed
                    and not locked
                    and not attempted
                ):
                    attempted = True
                    if not await self._connect_game_peer(base_url, room_code, http):
                        return
                if self._joiner.peer is not None and self._joiner.peer.closed:
                    if not self._relay_enabled:
                        self.peer_unavailable(
                            "Kết nối P2P đã mất. Bấm Thử kết nối lại; relay dữ liệu đã tắt."
                        )
                        return
                    self._publish(connection_kind="relay")
                await asyncio.sleep(60 if document["world_ready"] and not locked else 15)
            except asyncio.CancelledError:
                raise
            except (NetworkError, ValueError, KeyError):
                failures += 1
                if not await self._retry_lobby(failures):
                    return

    async def _retry_lobby(self, failures: int) -> bool:
        peer = self._joiner.peer if self._joiner is not None else None
        live = peer is not None and not peer.closed
        if failures >= 3 and not self._relay_enabled and not live:
            self.peer_unavailable(
                "Không liên lạc được với phòng. Kiểm tra mạng và bấm Thử kết nối lại."
            )
            return False
        self._publish(
            connection_note=(
                "Không liên lạc được với dịch vụ phòng. "
                "Kết nối P2P hiện tại vẫn hoạt động; đang thử kiểm tra lại."
            )
            if live
            else "Đang thử liên lạc lại với phòng…"
        )
        await asyncio.sleep(60 if live else 15)
        return True

    async def _connect_game_peer(self, base_url: str, room_code: str, http: HttpClient) -> bool:
        try:
            from nostalgia.multiplayer.peer_connection import connect_peer
            from nostalgia.multiplayer.peer_mux import PeerMux

            self._publish(
                connection_kind="connecting", connection_note="", connection_retryable=False
            )
            stream = await connect_peer(base_url, room_code, "game", http)
            if self._joiner is None:
                await stream.close()
                return True
            joiner = self._joiner
            joiner.peer = PeerMux(
                stream, on_closed=lambda peer: self._game_peer_closed(joiner, peer)
            )
            self._publish(
                connection_kind="direct",
                world_ready=True,
                connection_note="",
                connection_retryable=False,
            )
        except PeerConnectionError as exc:
            if not self._relay_enabled:
                self.peer_unavailable(str(exc), retryable=exc.retryable)
                return False
            self._publish(connection_kind="relay")
        except (ImportError, ConnectionError, TimeoutError, NetworkError):
            if not self._relay_enabled:
                self.peer_unavailable(
                    "Không thể kết nối P2P. Mạng có thể chặn UDP; relay dữ liệu đã tắt. "
                    "Thử mạng khác rồi bấm Thử kết nối lại."
                )
                return False
            self._publish(connection_kind="relay")
        except MultiplayerError as exc:
            self.peer_unavailable(str(exc), retryable=False)
            return False
        return True

    def _game_peer_closed(self, joiner: JoinerBridge, peer: PeerMux) -> None:
        if self._joiner is not joiner or joiner.peer is not peer:
            return
        if self._relay_enabled:
            self._publish(connection_kind="relay")
        else:
            self.peer_unavailable("Kết nối P2P đã mất. Bấm Thử kết nối lại; relay dữ liệu đã tắt.")
            if self._network_task is not None:
                self._network_task.cancel()

    def peer_unavailable(self, message: str, *, retryable: bool = True) -> None:
        self._publish(
            connection_kind="failed",
            world_ready=False,
            connection_note=message,
            connection_retryable=retryable,
        )
        self._on_failure(message)
