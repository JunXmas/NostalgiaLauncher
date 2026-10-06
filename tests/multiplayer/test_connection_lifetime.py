"""Heartbeat thật trên TCP và gói bắt tay có dấu Forge/Unicode; không tăng tốc game."""

from __future__ import annotations

import asyncio

import pytest
from fake_relay import FakeRelay, ServerSocket
from test_end_to_end import FakeWorld, setup
from test_gate import MC_HANDSHAKE, run_pair

from nostalgia.multiplayer.room_code import make_room_code


def varint(value: int) -> bytes:
    encoded = bytearray()
    while value > 127:
        encoded.append((value & 127) | 128)
        value >>= 7
    return bytes(encoded) + bytes([value])


@pytest.mark.parametrize("hostname", [b"localhost\0FML3\0", "界".encode() * 255])
def test_modded_and_utf8_handshakes_are_forwarded_unchanged(hostname: bytes) -> None:
    body = b"\0" + varint(763) + varint(len(hostname)) + hostname + b"\x63\xdd\x02"
    packet = varint(len(body)) + body
    _, accepted = run_pair("SECRET", "SECRET", packet)
    assert accepted is not None and accepted.verdict == "accepted"
    assert accepted.forward == packet


def test_idle_connection_survives_several_heartbeat_rounds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("nostalgia.net.websocket.PING_INTERVAL_SECONDS", 0.04)
    monkeypatch.setattr("nostalgia.net.websocket.PONG_TIMEOUT_SECONDS", 0.1)

    async def scenario() -> None:
        relay, world = FakeRelay(), FakeWorld()
        await relay.start()
        await world.start()
        host, joiner = await setup(relay, world, make_room_code())
        reader, writer = await asyncio.open_connection("127.0.0.1", joiner.local_port)
        try:
            writer.write(MC_HANDSHAKE)
            await writer.drain()
            assert (
                await asyncio.wait_for(reader.readexactly(len(MC_HANDSHAKE)), 2)
                == MC_HANDSHAKE[::-1]
            )
            await asyncio.sleep(0.35)
            assert host.joiner_count == 1
            writer.write(b"still the same connection")
            await writer.drain()
            assert (
                await asyncio.wait_for(reader.readexactly(25), 2)
                == b"still the same connection"[::-1]
            )
        finally:
            writer.close()
            await joiner.stop()
            await host.stop()
            await asyncio.gather(world.stop(), relay.stop())

    asyncio.run(scenario())


def test_unmatched_pong_closes_stalled_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("nostalgia.net.websocket.PING_INTERVAL_SECONDS", 0.03)
    monkeypatch.setattr("nostalgia.net.websocket.PONG_TIMEOUT_SECONDS", 0.05)
    original_send = ServerSocket.send

    async def corrupt_pong(self: ServerSocket, payload: bytes, opcode: int = 2) -> None:
        await original_send(self, b"wrong nonce" if opcode == 10 else payload, opcode)

    monkeypatch.setattr(ServerSocket, "send", corrupt_pong)

    async def scenario() -> None:
        relay, world = FakeRelay(), FakeWorld()
        await relay.start()
        await world.start()
        host, joiner = await setup(relay, world, make_room_code())
        try:
            await asyncio.wait_for(host.wait_closed(), 1)
            assert host._socket is not None and host._socket.closed
            assert not host._pumps and not host._worlds
        finally:
            await joiner.stop()
            await host.stop()
            await asyncio.gather(world.stop(), relay.stop())

    asyncio.run(scenario())
