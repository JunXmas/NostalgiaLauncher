"""Luật L3 (chỉ tin beacon từ loopback, cổng hợp lệ) và L9 (kiểm Sec-WebSocket-Accept)."""

from __future__ import annotations

import asyncio

import pytest
from fake_relay import FakeRelay

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.lan import build_beacon, parse_lan_beacon
from nostalgia.net.websocket import MAX_FRAME_BYTES, WebSocketClient


def test_lan_detect_ignores_non_loopback_source() -> None:
    beacon = build_beacon(25565, "Thế giới của Jun")
    found = parse_lan_beacon(beacon, "127.0.0.1")
    assert found is not None and (found.world_port, found.world_name) == (25565, "Thế giới của Jun")
    assert parse_lan_beacon(beacon, "192.168.1.7") is None  # máy khác trong LAN
    assert parse_lan_beacon(beacon, "::1") is None  # IPv6 không dùng cho multicast v4
    # Minecraft phát qua card LAN nên nguồn là IP LAN của CHÍNH máy này: phải nhận.
    mine = frozenset({"127.0.0.1", "192.168.1.17"})
    assert parse_lan_beacon(beacon, "192.168.1.17", mine) is not None
    assert parse_lan_beacon(beacon, "192.168.1.7", mine) is None


@pytest.mark.parametrize("bad_port", [22, 0, 1023, 65536, 99999])
def test_lan_detect_rejects_bad_port(bad_port: int) -> None:
    assert parse_lan_beacon(build_beacon(bad_port, "x"), "127.0.0.1") is None
    assert parse_lan_beacon(b"[MOTD]x[/MOTD]", "127.0.0.1") is None


def test_websocket_accept_is_verified() -> None:
    async def scenario() -> None:
        async def bad_server(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            while (await reader.readline()) not in (b"\r\n", b""):
                pass
            writer.write(
                b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                b"Sec-WebSocket-Accept: bogus=\r\n\r\n"
            )
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(bad_server, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        with pytest.raises(MultiplayerError, match="Sec-WebSocket-Accept"):
            await WebSocketClient.connect(f"ws://127.0.0.1:{port}/s/ABC?role=join")
        server.close()
        await server.wait_closed()

    asyncio.run(scenario())


def test_frame_caps() -> None:
    async def scenario() -> None:
        relay = FakeRelay()
        await relay.start()
        host = await WebSocketClient.connect(f"{relay.url}/s/ROOM01?role=host")
        joiner = await WebSocketClient.connect(f"{relay.url}/s/ROOM01?role=join")
        opened = await host.receive()
        assert opened[4] == 1  # OPEN
        await joiner.send(b"x" * 70000)  # hơn 65535: khung 64-bit, vẫn dưới trần
        assert len(await host.receive()) == 70000 + 5
        room = relay.rooms["ROOM01"]
        assert room.host is not None
        await room.host.send(b"y" * (MAX_FRAME_BYTES + 1))  # relay lỗi/độc: vượt trần → đóng
        assert await host.receive() == b""
        assert host.closed
        await joiner.close()
        await relay.stop()

    asyncio.run(scenario())
