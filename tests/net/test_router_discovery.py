"""Thiết bị SSDP không được đưa launcher tới máy khác hoặc nạp XML ngoài."""

import asyncio

import pytest

from nostalgia.net.router_discovery import parse_router
from nostalgia.net.router_http import fetch_router, is_router_address


def description(control: str) -> bytes:
    return (
        '<root xmlns="urn:schemas-upnp-org:device-1-0"><device><serviceList><service>'
        "<serviceType>urn:schemas-upnp-org:service:WANIPConnection:1</serviceType>"
        f"<controlURL>{control}</controlURL></service></serviceList></device></root>"
    ).encode()


@pytest.mark.parametrize(
    "control",
    [
        "http://8.8.8.8/control",
        "http://evil.invalid/c",
        "http://u:p@192.168.1.1/c",
        "https://192.168.1.1/c",
    ],
)
def test_router_description_cannot_redirect_control_requests(control: str) -> None:
    with pytest.raises(ValueError):
        parse_router(
            description(control), "http://192.168.1.1/device.xml", "192.168.1.1", "192.168.1.10"
        )


def test_relative_control_url_is_allowed_but_dtd_is_not() -> None:
    service = parse_router(
        description("/control"), "http://192.168.1.1/device.xml", "192.168.1.1", "192.168.1.10"
    )
    assert service.control_url == "http://192.168.1.1/control"
    with pytest.raises(ValueError):
        parse_router(
            b'<!DOCTYPE root [<!ENTITY x "bad">]>' + description("/control"),
            "http://192.168.1.1/device.xml",
            "192.168.1.1",
            "192.168.1.10",
        )


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "0.0.0.0", "169.254.1.1", "100.64.0.1", "8.8.8.8", "router.invalid", "::1"],
)
def test_router_http_rejects_non_lan_addresses_without_connecting(address: str) -> None:
    assert not is_router_address(address)
    with pytest.raises(ValueError):
        asyncio.run(fetch_router(f"http://{address}/control", address))
