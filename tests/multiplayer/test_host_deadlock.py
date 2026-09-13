"""Một client bị nghẽn TCP buffer không được đóng băng toàn bộ relay server."""

from __future__ import annotations

import asyncio
import contextlib

from fake_relay import FakeRelay
from test_gate import MC_HANDSHAKE

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.room_code import make_room_code, split_room_code


class SlowWorld:
    """Server giả: echo ngược byte nhưng một kết nối được phép chậm tuỳ ý."""

    def __init__(self) -> None:
        self.connections = 0
        self.port = 0
        self._slow_streams: set[int] = set()
        self._connection_id = 0

    def make_slow(self, connection_index: int) -> None:
        self._slow_streams.add(connection_index)

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._connection_id += 1
        this_id = self._connection_id
        self.connections += 1
        try:
            while chunk := await reader.read(65536):
                if this_id in self._slow_streams:
                    # Giả lập client bị nghẽn: không đọc, ngủ mãi.
                    await asyncio.sleep(3600)
                writer.write(chunk[::-1])
                await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            writer.close()

    async def stop(self) -> None:
        self._server.close()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._server.wait_closed(), 1)


async def _setup(
    relay: FakeRelay, world: SlowWorld, room_code: str
) -> tuple[HostRelay, JoinerBridge]:
    room_id, room_secret = split_room_code(room_code)
    host = HostRelay(relay.url, room_id, room_secret, world.port)
    await host.connect()
    host.start()
    joiner = JoinerBridge(relay.url, room_id, room_secret)
    await joiner.start()
    return host, joiner


async def _game_client(local_port: int, payload: bytes = MC_HANDSHAKE) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", local_port)
    writer.write(payload)
    await writer.drain()
    try:
        return await asyncio.wait_for(reader.readexactly(len(payload)), 3)
    except (TimeoutError, asyncio.IncompleteReadError):
        return b""
    finally:
        writer.close()


def test_stuck_client_does_not_block_other_players() -> None:
    """Khi một joiner bị nghẽn TCP buffer, các joiner khác vẫn nhận được dữ liệu."""

    async def scenario() -> None:
        relay, world = FakeRelay(), SlowWorld()
        await relay.start()
        await world.start()
        room_code = make_room_code()

        # Joiner 1: sẽ bị nghẽn (world connection 1 chậm)
        world.make_slow(1)
        host, joiner1 = await _setup(relay, world, room_code)
        room_id, room_secret = split_room_code(room_code)

        # Kết nối joiner 1 trước (sẽ bị nghẽn ở phía world)
        reader1, writer1 = await asyncio.open_connection("127.0.0.1", joiner1.local_port)
        writer1.write(MC_HANDSHAKE)
        await writer1.drain()
        await asyncio.sleep(0.15)

        # Joiner 2: kết nối bình thường, PHẢI vẫn hoạt động
        joiner2 = JoinerBridge(relay.url, room_id, room_secret)
        await joiner2.start()

        # Joiner 2 gửi và nhận dữ liệu — không bị ảnh hưởng bởi joiner 1
        result = await _game_client(joiner2.local_port)
        assert result == MC_HANDSHAKE[::-1], "joiner 2 phải nhận dữ liệu bình thường"

        # Dọn dẹp
        writer1.close()
        await joiner2.stop()
        await joiner1.stop()
        await host.stop()
        await asyncio.gather(world.stop(), relay.stop())

    asyncio.run(scenario())
