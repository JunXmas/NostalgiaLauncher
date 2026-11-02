"""Ánh xạ UDP thật qua IGD giả: không đè cổng, có lease và dọn cả khi huỷ."""

import asyncio

import pytest

from nostalgia.net.router_mapping import create_mapping, remove_mapping, renew_mapping
from router_fixture import FakeRouter


def test_mapping_renews_and_removes_only_its_own_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "nostalgia.net.router_http.is_router_address", lambda address: address == "127.0.0.1"
    )

    async def scenario() -> None:
        router = FakeRouter()
        server = await asyncio.start_server(router.serve, "127.0.0.1", 0)
        async with server:
            service = router.service(server.sockets[0].getsockname()[1])
            mapping = await create_mapping(service, 45678)
            assert mapping.external_address == "8.8.8.8" and mapping.external_port == 45678
            assert router.mappings[45678]["NewInternalPort"] == "45678"
            await renew_mapping(mapping)
            assert router.actions.count("AddPortMapping") == 2
            await remove_mapping(mapping)
            assert not router.mappings
            await remove_mapping(mapping)
            assert router.actions.count("DeletePortMapping") == 1
            mapping = await create_mapping(service, 45678)
            router.mappings[45678]["NewPortMappingDescription"] = "Another program"
            await remove_mapping(mapping)
            assert 45678 in router.mappings
            with pytest.raises(ValueError, match="ownership changed"):
                await renew_mapping(mapping)
            with pytest.raises(ValueError, match="already mapped"):
                await create_mapping(service, 45678)
            assert router.actions.count("AddPortMapping") == 3

    asyncio.run(scenario())


def test_cgnat_is_rejected_before_opening_a_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "nostalgia.net.router_http.is_router_address", lambda address: address == "127.0.0.1"
    )

    async def scenario() -> None:
        router = FakeRouter()
        router.address = "100.64.0.1"
        server = await asyncio.start_server(router.serve, "127.0.0.1", 0)
        async with server:
            with pytest.raises(ValueError, match="no public IPv4"):
                await create_mapping(router.service(server.sockets[0].getsockname()[1]), 45678)
            assert not router.mappings and "AddPortMapping" not in router.actions

    asyncio.run(scenario())


def test_cancel_after_router_opens_port_still_removes_our_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "nostalgia.net.router_http.is_router_address", lambda address: address == "127.0.0.1"
    )

    async def scenario() -> None:
        router = FakeRouter()
        router.delay_add = True
        server = await asyncio.start_server(router.serve, "127.0.0.1", 0)
        async with server:
            task = asyncio.create_task(
                create_mapping(router.service(server.sockets[0].getsockname()[1]), 45678)
            )
            await asyncio.wait_for(router.added.wait(), 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert not router.mappings
            await asyncio.sleep(0.15)

    asyncio.run(scenario())
