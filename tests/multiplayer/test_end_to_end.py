"""Trọn đường game-joiner → proxy → relay giả → host → world giả, và các luật L2/L5/L6/L7/L10."""

from __future__ import annotations

import asyncio
import contextlib

import pytest
from fake_relay import FakeRelay
from test_gate import MC_HANDSHAKE

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.room_code import make_room_code, split_room_code


class FakeWorld:
    """Server "Minecraft" giả trên loopback: echo ngược mọi byte, đếm kết nối."""

    def __init__(self) -> None:
        self.connections = 0
        self.port = 0

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._echo, "127.0.0.1", 0)
        self.port = self._server.sockets[0].getsockname()[1]

    async def _echo(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.connections += 1
        while chunk := await reader.read(65536):
            writer.write(chunk[::-1])
            await writer.drain()
        writer.close()

    async def stop(self) -> None:
        self._server.close()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._server.wait_closed(), 1)


async def setup(
    relay: FakeRelay, world: FakeWorld, room_code: str
) -> tuple[HostRelay, JoinerBridge]:
    room_id, room_secret = split_room_code(room_code)
    host = HostRelay(relay.url, room_id, room_secret, world.port)
    await host.connect()
    host.start()
    joiner = JoinerBridge(relay.url, room_id, room_secret)
    await joiner.start()
    return host, joiner


async def game_client(local_port: int, payload: bytes = MC_HANDSHAKE) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", local_port)
    writer.write(payload)
    await writer.drain()
    try:
        return await asyncio.wait_for(reader.readexactly(len(payload)), 3)
    except (TimeoutError, asyncio.IncompleteReadError):
        return b""
    finally:
        writer.close()


def test_secret_never_on_the_wire_and_bytes_reach_the_world() -> None:
    async def scenario() -> None:
        relay, world = FakeRelay(), FakeWorld()
        await relay.start()
        await world.start()
        room_code = make_room_code()
        host, joiner = await setup(relay, world, room_code)
        assert joiner.local_port > 0
        assert await game_client(joiner.local_port) == MC_HANDSHAKE[::-1]
        assert world.connections == 1 and host.joiner_count == 1
        _, room_secret = split_room_code(room_code)
        assert room_secret.encode() not in bytes(relay.wire)
        assert room_secret.lower().encode() not in bytes(relay.wire)
        await joiner.stop()
        await host.stop()
        await asyncio.gather(world.stop(), relay.stop())

    asyncio.run(scenario())


def test_wrong_secret_and_non_minecraft_bytes_never_touch_the_world() -> None:
    async def scenario() -> None:
        relay, world = FakeRelay(), FakeWorld()
        await relay.start()
        await world.start()
        room_code = make_room_code()
        host, joiner = await setup(relay, world, room_code)
        room_id, _ = split_room_code(room_code)
        impostor = JoinerBridge(relay.url, room_id, "WRONGSECRET1")
        await impostor.start()
        assert await game_client(impostor.local_port) == b""
        with pytest.raises(ConnectionError, match="mã phòng"):
            await impostor.probe()
        assert await game_client(joiner.local_port, b"GET / HTTP/1.1\r\n\r\n") == b""
        await asyncio.sleep(0.1)
        assert world.connections == 0
        await asyncio.gather(impostor.stop(), joiner.stop(), host.stop())
        await asyncio.gather(world.stop(), relay.stop())

    asyncio.run(scenario())


def test_locked_room_refuses_new_streams_but_keeps_current_players() -> None:
    async def scenario() -> None:
        relay, world = FakeRelay(), FakeWorld()
        await relay.start()
        await world.start()
        host, joiner = await setup(relay, world, make_room_code())
        reader, writer = await asyncio.open_connection("127.0.0.1", joiner.local_port)
        writer.write(MC_HANDSHAKE)
        await writer.drain()
        assert await asyncio.wait_for(reader.readexactly(len(MC_HANDSHAKE)), 3)
        host.locked = True
        assert await game_client(joiner.local_port) == b""
        writer.write(b"abc")
        await writer.drain()
        assert await asyncio.wait_for(reader.readexactly(3), 3) == b"cba"
        writer.close()
        await joiner.stop()
        await host.stop()
        await asyncio.gather(world.stop(), relay.stop())

    asyncio.run(scenario())


def test_bridge_binds_loopback_only_and_stop_ends_all_tasks() -> None:
    async def scenario() -> None:
        relay, world = FakeRelay(), FakeWorld()
        await relay.start()
        await world.start()
        host, joiner = await setup(relay, world, make_room_code())
        assert joiner._server is not None
        assert joiner._server.sockets[0].getsockname()[0] == "127.0.0.1"
        reader, writer = await asyncio.open_connection("127.0.0.1", joiner.local_port)
        writer.write(MC_HANDSHAKE)
        await writer.drain()
        await asyncio.wait_for(reader.readexactly(len(MC_HANDSHAKE)), 3)
        before = len(asyncio.all_tasks())
        await asyncio.wait_for(joiner.stop(), 2)
        await asyncio.wait_for(host.stop(), 2)
        await asyncio.sleep(0.05)
        assert len(asyncio.all_tasks()) < before
        assert await reader.read(1) == b""  # game thấy kết nối đóng
        writer.close()
        await asyncio.gather(world.stop(), relay.stop())

    asyncio.run(scenario())
