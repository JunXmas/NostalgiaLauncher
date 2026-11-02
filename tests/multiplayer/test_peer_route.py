"""Ứng viên UPnP trỏ đúng socket ICE thật và lease dừng cùng peer."""

import asyncio

import pytest

pytest.importorskip("aiortc")
from aiortc import RTCConfiguration, RTCPeerConnection

from nostalgia.multiplayer.peer_route import PeerRoute
from nostalgia.net.router_discovery import RouterService
from nostalgia.net.router_mapping import RouterMapping


def test_upnp_candidate_uses_the_existing_ice_socket_and_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("aioice.ice.get_host_addresses", lambda **_kwargs: ["127.0.0.1"])
    monkeypatch.setattr("nostalgia.multiplayer.peer_route.is_router_address", lambda _address: True)
    mappings: list[RouterMapping] = []
    removed: list[RouterMapping] = []

    async def discover(_address: str) -> RouterService:
        return RouterService("192.168.1.1", "http://192.168.1.1/control", "service", "127.0.0.1")

    async def create(service: RouterService, port: int) -> RouterMapping:
        mapping = RouterMapping(service, "8.8.8.8", port, port, "fixture")
        mappings.append(mapping)
        return mapping

    async def remove(mapping: RouterMapping) -> None:
        removed.append(mapping)

    monkeypatch.setattr("nostalgia.multiplayer.peer_route.discover_router", discover)
    monkeypatch.setattr("nostalgia.multiplayer.peer_route.create_mapping", create)
    monkeypatch.setattr("nostalgia.multiplayer.peer_route.remove_mapping", remove)

    async def scenario() -> None:
        connection = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        connection.createDataChannel("fixture")
        route = PeerRoute(connection)
        try:
            await route.prepare()
            assert connection.sctp is not None
            gatherer = connection.sctp.transport.transport.iceGatherer
            candidates = gatherer.getLocalCandidates()
            host = next(candidate for candidate in candidates if candidate.type == "host")
            mapped = next(candidate for candidate in candidates if candidate.type == "srflx")
            assert mapped.ip == "8.8.8.8" and mapped.port == host.port
            assert mapped.relatedAddress == host.ip and mapped.relatedPort == host.port
            assert len(mappings) == 1 and route._renewal is not None
        finally:
            await connection.close()
            await route.close()
            await route.close()
        assert removed == mappings and route._renewal is not None and route._renewal.done()

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "failure",
    [
        asyncio.LimitOverrunError("header > 8 KiB", 8192),  # thiết bị LAN trả header quá dài
        IndexError("status line without spaces"),
        AttributeError("aioice renamed _local_candidates"),
    ],
)
def test_upnp_failures_fall_back_to_ipv6_and_stun_instead_of_breaking_p2p(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    monkeypatch.setattr("aioice.ice.get_host_addresses", lambda **_kwargs: ["127.0.0.1"])
    monkeypatch.setattr("nostalgia.multiplayer.peer_route.is_router_address", lambda _address: True)

    async def discover(_address: str) -> RouterService:
        raise failure

    monkeypatch.setattr("nostalgia.multiplayer.peer_route.discover_router", discover)

    async def scenario() -> None:
        connection = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        connection.createDataChannel("fixture")
        route = PeerRoute(connection)
        try:
            await route.prepare()
            assert connection.sctp is not None
            gatherer = connection.sctp.transport.transport.iceGatherer
            assert any(c.type == "host" for c in gatherer.getLocalCandidates())
        finally:
            await connection.close()
            await route.close()

    asyncio.run(scenario())


def test_close_survives_a_renewal_task_that_died() -> None:
    async def scenario() -> None:
        route = PeerRoute.__new__(PeerRoute)
        route._mappings, route._closed = [], False

        async def died() -> None:
            raise asyncio.IncompleteReadError(b"", 10)

        route._renewal = asyncio.ensure_future(died())
        await asyncio.sleep(0)
        await route.close()  # không được ném lại lỗi của task gia hạn

    asyncio.run(scenario())
