"""Host chỉ nối Minecraft cục bộ hoặc đọc khối trong snapshot đã được cấp quyền."""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from typing import TYPE_CHECKING

from nostalgia.multiplayer.mux import PEER_RESPONSE, pack_mux_frame
from nostalgia.multiplayer.peer_connection import answer_peer, build_peer_configuration
from nostalgia.multiplayer.peer_stream import PeerStream
from nostalgia.multiplayer.sync_chunk import read_sync_chunk

if TYPE_CHECKING:
    from aiortc import RTCDataChannel, RTCPeerConnection

    from nostalgia.multiplayer.host import HostRelay


class PeerHost:
    def __init__(self, host: HostRelay) -> None:
        self.host = host
        self.connections: set[RTCPeerConnection] = set()
        self.games: set[HostRelay] = set()
        self.tasks: set[asyncio.Task[None]] = set()
        self._seen: dict[str, float] = {}

    @property
    def joiner_count(self) -> int:
        return sum(game.joiner_count for game in self.games)

    def request(self, payload: bytes) -> None:
        if len(self.connections) >= 16 or len(payload) > 96000:
            return
        task = asyncio.create_task(self._answer(payload))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def _answer(self, payload: bytes) -> None:
        connection = None
        try:
            from aiortc import RTCPeerConnection

            document = json.loads(payload)
            request_id, purpose = document["id"], document["purpose"]
            deadline = document["expires_at"]
            self._seen = {
                key: expires for key, expires in self._seen.items() if expires > time.time()
            }
            if (
                purpose not in ("game", "sync")
                or not isinstance(request_id, str)
                or len(request_id) != 32
                or request_id in self._seen
                or not isinstance(deadline, int)
                or not time.time() < deadline <= time.time() + 46
                or self.host.locked
                or (purpose == "game" and self.host.world_port == 0)
                or (purpose == "sync" and self.host.sync_snapshot is None)
                or len(self.connections) >= 16
            ):
                return
            self._seen[request_id] = time.time() + 120
            connection = RTCPeerConnection(build_peer_configuration())
            self.connections.add(connection)

            channel_received = False

            @connection.on("datachannel")
            def channel_arrived(channel: RTCDataChannel) -> None:
                nonlocal channel_received
                if (
                    channel_received
                    or channel.label != "nostalgia-" + purpose
                    or not channel.ordered
                ):
                    channel.close()
                    return
                channel_received = True
                stream = PeerStream(connection, channel)
                task = asyncio.create_task(self._serve(stream, purpose, deadline))
                self.tasks.add(task)
                task.add_done_callback(self.tasks.discard)

            async with asyncio.timeout(12):
                answer = await answer_peer(
                    connection, self.host.room_secret, request_id, purpose, document["body"]
                )
                if self.host._socket is None:
                    raise ConnectionError("room closed")
                await self.host._socket.send(
                    pack_mux_frame(
                        0, PEER_RESPONSE, json.dumps({"id": request_id, "body": answer}).encode()
                    )
                )
            # Đầu kết nối chưa mở kênh không được giữ chỗ vô hạn.
            await asyncio.sleep(15)
            if connection.connectionState != "connected" or not channel_received:
                await asyncio.shield(connection.close())
                self.connections.discard(connection)
        except (Exception, asyncio.CancelledError):
            if connection is not None:
                await asyncio.shield(connection.close())
                self.connections.discard(connection)

    async def _serve(self, stream: PeerStream, purpose: str, deadline: int) -> None:
        from nostalgia.multiplayer.host import HostRelay

        game = None
        try:
            await stream.wait_open()
            if purpose == "game":
                game = HostRelay(
                    "",
                    "",
                    self.host.room_secret,
                    self.host.world_port,
                    on_joiners_changed=lambda _count: self.host._notify(),
                    admission=lambda: (
                        not self.host.locked and self.host.joiner_count < self.host.max_joiners
                    ),
                )
                game._socket = stream
                self.games.add(game)
                await game.run()
            else:
                async with asyncio.timeout(max(0, deadline - time.time())):
                    while payload := await stream.receive():
                        if len(payload) > 1024:
                            break
                        reply = await asyncio.to_thread(
                            read_sync_chunk, self.host.sync_snapshot, payload
                        )
                        if not reply:
                            break
                        await stream.send(reply)
        except (Exception, asyncio.CancelledError):
            pass
        finally:
            if game is not None:
                self.games.discard(game)
                self.host._notify()
            await stream.close()
            self.connections.discard(stream.connection)

    async def close(self) -> None:
        tasks = tuple(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for connection in tuple(self.connections):
            with contextlib.suppress(Exception):
                await asyncio.shield(connection.close())
        self.connections.clear()
