"""Thử lại đường P2P trong cùng phòng; giữ proxy và bản chơi khách đã đồng bộ."""

from __future__ import annotations

import asyncio
import contextlib
from concurrent.futures import Future
from typing import TYPE_CHECKING

from nostalgia.multiplayer.room_watch import RoomWatch

if TYPE_CHECKING:
    from nostalgia.multiplayer.model import RoomStatus


class RoomRecovery(RoomWatch):
    _status: RoomStatus

    def _submit(self, coroutine: object) -> Future[None]:
        raise NotImplementedError

    def retry_connection(self) -> Future[None]:
        return self._submit(self._retry_guest_connection())

    async def _retry_guest_connection(self) -> None:
        joiner, room_code = self._joiner, self._guest_room_code
        if (
            joiner is None
            or not room_code
            or self._status.role != "joined"
            or self._status.connection_kind != "failed"
            or not self._status.connection_retryable
        ):
            return
        self._publish(
            connection_kind="pending",
            connection_note="",
            connection_retryable=False,
            world_ready=False,
        )
        task, self._network_task = self._network_task, None
        if task is not None:
            task.cancel()
            with contextlib.suppress(Exception, asyncio.CancelledError):
                await task
        peer, joiner.peer = joiner.peer, None
        if peer is not None:
            try:
                await peer.close()
            except Exception:
                if self._joiner is joiner:
                    self.peer_unavailable(
                        "Chưa dọn được kết nối cũ. Hãy rời phòng rồi nhận lại lời mời.",
                        retryable=False,
                    )
                return
        # Rời phòng trong lúc dọn socket cũ không được làm phòng sống lại.
        if self._joiner is joiner and self._status.role == "joined":
            self.watch_guest_room(room_code)
