"""Chunk game lớn phải tới đủ dù Minecraft phía nhận tạm thời đọc chậm."""

import asyncio
from typing import cast

import pytest
from test_gate import MC_HANDSHAKE
from test_peer_transport import Signalling, local_ice

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.peer_connection import connect_peer
from nostalgia.multiplayer.peer_host import PeerHost
from nostalgia.multiplayer.peer_mux import PeerMux
from nostalgia.net.http import HttpClient


def test_slow_game_consumer_does_not_overflow_or_lose_chunk_packets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_ice(monkeypatch)
    payload = b"minecraft chunk data" * (600 * 1024)

    async def scenario() -> None:
        world_finished = asyncio.Event()

        async def world(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            try:
                assert await reader.readexactly(len(MC_HANDSHAKE)) == MC_HANDSHAKE
                writer.write(payload)
                await writer.drain()
                await reader.read()
            finally:
                writer.close()
                world_finished.set()

        server = await asyncio.start_server(world, "127.0.0.1", 0)
        host = HostRelay("", "ABCDEF", "ABCDEFGHJKMN", server.sockets[0].getsockname()[1])
        host.peer = PeerHost(host)
        signal = Signalling(host)
        host._socket = signal

        class Http:
            send = signal.send_http

        guest = JoinerBridge("ws://unused", "ABCDEF", "ABCDEFGHJKMN")
        writer = None
        try:
            peer = await connect_peer(
                "https://signal.test", "ABCDEFABCDEFGHJKMN", "game", cast(HttpClient, Http())
            )
            guest.peer = PeerMux(peer)
            await guest.start()
            reader, writer = await asyncio.open_connection("127.0.0.1", guest.local_port)
            writer.write(MC_HANDSHAKE)
            await writer.drain()
            await asyncio.sleep(1)
            assert not peer.closed
            received = await asyncio.wait_for(reader.readexactly(len(payload)), 20)
            assert received == payload
            assert signal.purposes == ["game"]
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()
            await asyncio.wait_for(guest.stop(), 5)
            await asyncio.wait_for(host.close(), 5)
            server.close()
            await server.wait_closed()
            await asyncio.wait_for(world_finished.wait(), 5)

    asyncio.run(scenario())
