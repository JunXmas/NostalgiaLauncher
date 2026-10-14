"""STUN thật qua UDP cục bộ: máy chính lỗi, máy dự phòng đáp, LAN và huỷ thao tác."""

import asyncio
import time
from typing import cast

import pytest
from aioice import stun
from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection

from nostalgia.multiplayer.peer_stun import select_peer_configuration


class StunServer(asyncio.DatagramProtocol):
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.requests = 0
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self.transport = cast(asyncio.DatagramTransport, transport)

    def datagram_received(self, payload: bytes, address: tuple[str, int]) -> None:
        self.requests += 1
        if self.mode == "silent":
            return
        request = stun.parse_message(payload)
        response = stun.Message(
            stun.Method.BINDING,
            stun.Class.RESPONSE,
            transaction_id=b"wrong-id-123" if self.mode == "wrong-id" else request.transaction_id,
            attributes={} if self.mode == "no-mapping" else {"XOR-MAPPED-ADDRESS": address},
        )
        assert self.transport is not None
        self.transport.sendto(bytes(response), address)


async def server(mode: str) -> tuple[asyncio.DatagramTransport, StunServer, str]:
    transport, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
        lambda: StunServer(mode), local_addr=("127.0.0.1", 0)
    )
    uri = "stun:127.0.0.1:" + str(transport.get_extra_info("sockname")[1])
    return transport, protocol, uri


@pytest.mark.parametrize("mode", ["silent", "wrong-id", "no-mapping"])
def test_unusable_primary_selects_working_fallback_and_gathers_real_candidates(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    async def scenario() -> None:
        primary, first, first_uri = await server(mode)
        fallback, second, second_uri = await server("valid")
        monkeypatch.setattr("nostalgia.multiplayer.peer_stun.FALLBACK_STUN_SERVERS", (second_uri,))
        monkeypatch.setattr("aioice.ice.get_host_addresses", lambda **_kw: ["127.0.0.1"])
        connection = None
        try:
            configuration = await select_peer_configuration(
                RTCConfiguration(iceServers=[RTCIceServer(urls=first_uri)])
            )
            assert configuration.iceServers and configuration.iceServers[0].urls == second_uri
            assert first.requests and second.requests
            connection = RTCPeerConnection(configuration)
            connection.createDataChannel("nostalgia-game")
            await connection.setLocalDescription(await connection.createOffer())
            assert connection.localDescription is not None
            assert " typ srflx" in connection.localDescription.sdp
            assert second.requests >= 2, "ICE phải hỏi STUN bằng chính socket của kết nối"
        finally:
            if connection is not None:
                await connection.close()
            primary.close()
            fallback.close()

    asyncio.run(scenario())


def test_all_stun_servers_unavailable_is_bounded_and_keeps_local_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        transport, _protocol, uri = await server("silent")
        monkeypatch.setattr("nostalgia.multiplayer.peer_stun.FALLBACK_STUN_SERVERS", (uri,))
        monkeypatch.setattr("nostalgia.multiplayer.peer_stun.STUN_PROBE_TIMEOUT", 0.05)
        monkeypatch.setattr("aioice.ice.get_host_addresses", lambda **_kw: ["127.0.0.1"])
        connection = None
        try:
            started = time.monotonic()
            configuration = await select_peer_configuration(
                RTCConfiguration(iceServers=[RTCIceServer(urls=uri)])
            )
            assert not configuration.iceServers and time.monotonic() - started < 0.5
            connection = RTCPeerConnection(configuration)
            connection.createDataChannel("nostalgia-game")
            await connection.setLocalDescription(await connection.createOffer())
            assert connection.localDescription and " typ host" in connection.localDescription.sdp
            assert " typ relay" not in connection.localDescription.sdp
        finally:
            if connection is not None:
                await connection.close()
            transport.close()

    asyncio.run(scenario())


def test_cancelled_selection_cleans_up_probe_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    async def scenario() -> None:
        transport, protocol, uri = await server("silent")
        monkeypatch.setattr("nostalgia.multiplayer.peer_stun.FALLBACK_STUN_SERVERS", (uri,))
        selection = asyncio.create_task(
            select_peer_configuration(RTCConfiguration(iceServers=[RTCIceServer(urls=uri)]))
        )
        try:
            async with asyncio.timeout(1):
                while not protocol.requests:
                    await asyncio.sleep(0.01)
            selection.cancel()
            with pytest.raises(asyncio.CancelledError):
                await selection
            assert not [
                task for task in asyncio.all_tasks() if "_available_stun_server" in str(task)
            ]
        finally:
            selection.cancel()
            await asyncio.gather(selection, return_exceptions=True)
            transport.close()

    asyncio.run(scenario())


def test_explicit_local_only_configuration_does_not_start_any_probes() -> None:
    configuration = RTCConfiguration(iceServers=[])
    assert asyncio.run(select_peer_configuration(configuration)) is configuration
