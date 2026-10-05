"""Luật L5 phía host: quá MAX_PENDING stream chưa xác thực thì stream mới bị đóng ngay."""

from __future__ import annotations

import asyncio

from fake_relay import FakeRelay

from nostalgia.multiplayer.host import MAX_PENDING, HostRelay
from nostalgia.net.websocket import WebSocketClient


def test_pending_streams_capped() -> None:
    async def scenario() -> None:
        relay = FakeRelay()
        await relay.start()
        host = HostRelay(relay.url, "ROOM02", "SECRET", world_port=1)
        await host.connect()
        host.start()
        loiterers = []
        for _ in range(MAX_PENDING):
            loiterer = await WebSocketClient.connect(f"{relay.url}/s/ROOM02?role=join")
            await loiterer.send(b"NL")  # nửa magic: hợp lệ nhưng không bao giờ hoàn tất
            loiterers.append(loiterer)
        await asyncio.sleep(0.2)
        assert len(host._gates) == MAX_PENDING
        extra = await WebSocketClient.connect(f"{relay.url}/s/ROOM02?role=join")
        await extra.send(b"NL")
        assert await asyncio.wait_for(extra.receive(), 3) == b""  # bị đóng, không cấp buffer
        assert len(host._gates) == MAX_PENDING
        for loiterer in loiterers:
            await loiterer.close()
        await host.stop()
        await relay.stop()

    asyncio.run(scenario())
