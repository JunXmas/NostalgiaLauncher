"""Chọn STUN có phản hồi trước ICE; không chuyển gói game/file qua dịch vụ này."""

from __future__ import annotations

import asyncio
import logging
import socket
import struct
from dataclasses import replace
from typing import TYPE_CHECKING, cast
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from aiortc import RTCConfiguration

FALLBACK_STUN_SERVERS = (
    "stun:stun.l.google.com:19302",
    "stun:global.stun.twilio.com:3478",
)
STUN_PROBE_TIMEOUT = 2.0


class _StunProbe(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        from aioice import stun

        self.request = stun.Message(stun.Method.BINDING, stun.Class.REQUEST)
        self.result: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.DatagramTransport, transport)
        self.transport.sendto(bytes(self.request))

    def datagram_received(self, payload: bytes, _address: tuple[str, int]) -> None:
        from aioice import stun

        if (
            self.result.done()
            or not 20 <= len(payload) <= 4096
            or payload[4:8] != b"\x21\x12\xa4\x42"
        ):
            return
        try:
            response = stun.parse_message(payload)
            mapped = response.attributes.get("XOR-MAPPED-ADDRESS")
            if (
                response.message_method == stun.Method.BINDING
                and response.message_class == stun.Class.RESPONSE
                and response.transaction_id == self.request.transaction_id
                and isinstance(mapped, tuple)
                and len(mapped) == 2
            ):
                self.result.set_result(True)
        except (ValueError, struct.error, IndexError):
            pass

    def error_received(self, _error: Exception) -> None:
        if not self.result.done():
            self.result.set_result(False)

    def connection_lost(self, _error: Exception | None) -> None:
        if not self.result.done():
            self.result.set_result(False)


async def _available_stun_server(uri: str) -> str | None:
    probe = _StunProbe()
    try:
        address = urlsplit("//" + uri.removeprefix("stun:"))
        if not address.hostname:
            return None
        async with asyncio.timeout(STUN_PROBE_TIMEOUT):
            await asyncio.get_running_loop().create_datagram_endpoint(
                lambda: probe,
                remote_addr=(address.hostname, address.port or 3478),
                family=socket.AF_INET,
            )
            try:
                available = await asyncio.wait_for(asyncio.shield(probe.result), 0.6)
            except TimeoutError:
                assert probe.transport is not None
                probe.transport.sendto(bytes(probe.request))
                available = await probe.result
            return uri if available else None
    except (OSError, TimeoutError, ValueError):
        return None
    finally:
        if probe.transport is not None:
            probe.transport.close()


async def select_peer_configuration(configuration: RTCConfiguration) -> RTCConfiguration:
    """aiortc dùng STUN đầu tiên; chọn máy có phản hồi, hoặc giữ đường LAN khi đều lỗi."""
    from aiortc import RTCIceServer

    servers = configuration.iceServers or []
    if not servers:
        return configuration
    uris = [
        uri
        for server in servers
        for uri in (server.urls if isinstance(server.urls, list) else [server.urls])
    ]
    if not uris or any(not uri.startswith("stun:") for uri in uris):
        return configuration
    tasks = [
        asyncio.create_task(_available_stun_server(uri))
        for uri in dict.fromkeys([*uris, *FALLBACK_STUN_SERVERS])
    ]
    try:
        for completed in asyncio.as_completed(tasks):
            uri = await completed
            if uri:
                logging.getLogger(__name__).info("STUN discovery ready: %s", uri)
                return replace(configuration, iceServers=[RTCIceServer(urls=uri)])
        logging.getLogger(__name__).warning(
            "No STUN response; attempting local/direct ICE candidates"
        )
        return replace(configuration, iceServers=[])
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
