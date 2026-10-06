"""Kiểm tra relay lâu hơn 15 phút bằng world TCP giả, không chạy Minecraft thật."""

from __future__ import annotations

import argparse
import asyncio
import ssl
import time
from pathlib import Path

from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.host import HostRelay
from nostalgia.multiplayer.room_code import make_room_code, split_room_code
from nostalgia.repo.endpoints import DEFAULT_ENDPOINTS


async def echo(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while payload := await reader.read(65536):
            writer.write(payload)
            await writer.drain()
    finally:
        writer.close()


async def soak(relay_url: str, seconds: float, tls_context: ssl.SSLContext | None = None) -> None:
    world = await asyncio.start_server(echo, "127.0.0.1", 0)
    room_id, room_secret = split_room_code(make_room_code())
    host = HostRelay(
        relay_url, room_id, room_secret, world.sockets[0].getsockname()[1], tls_context=tls_context
    )
    joiner = JoinerBridge(relay_url, room_id, room_secret, tls_context=tls_context)
    writer = None
    started = time.monotonic()
    try:
        await host.connect()
        host.start()
        port = await joiner.start()
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        # Handshake Forge 1.20.1: dấu FML3 phải đi nguyên vẹn qua proxy.
        hostname = b"localhost\x00FML3\x00"
        body = b"\x00\xfb\x05" + bytes([len(hostname)]) + hostname + b"\x63\xdd\x02"
        payload = bytes([len(body)]) + body
        exchanges = 0
        while True:
            writer.write(payload)
            await writer.drain()
            assert await asyncio.wait_for(reader.readexactly(len(payload)), 20) == payload
            exchanges += 1
            elapsed = time.monotonic() - started
            print(
                f"elapsed={elapsed:.1f}s exchanges={exchanges} connections={host.joiner_count}",
                flush=True,
            )
            if elapsed >= seconds:
                break
            await asyncio.sleep(min(20, seconds - elapsed))
            payload = b"modpack-data\x00" * 512
        print(
            f"PASS {elapsed:.1f}s, one continuous TCP session (synthetic Forge payload)", flush=True
        )
    finally:
        if writer is not None:
            writer.close()
        await joiner.stop()
        await host.stop()
        world.close()
        await world.wait_closed()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relay", default=DEFAULT_ENDPOINTS.multiplayer_relay)
    parser.add_argument("--seconds", type=float, default=1020)
    parser.add_argument("--ca-cert", type=Path, help="CA của relay HTTPS cục bộ dùng trong test")
    arguments = parser.parse_args()
    tls_context = (
        ssl.create_default_context(cafile=arguments.ca_cert) if arguments.ca_cert else None
    )
    asyncio.run(soak(arguments.relay, arguments.seconds, tls_context))


if __name__ == "__main__":
    main()
