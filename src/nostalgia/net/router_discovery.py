"""Dò IGD bằng SSDP, chỉ chấp nhận URL của thiết bị đã trả lời trong LAN."""

from __future__ import annotations

import asyncio
import contextlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from nostalgia.net.router_http import fetch_router, is_router_address


@dataclass(frozen=True, slots=True)
class RouterService:
    address: str
    control_url: str
    service_type: str
    local_address: str


class _Discovery(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.responses: asyncio.Queue[tuple[bytes, str]] = asyncio.Queue(maxsize=4)

    def datagram_received(self, payload: bytes, address: tuple[str, int]) -> None:
        if len(payload) <= 8192 and is_router_address(address[0]):
            with contextlib.suppress(asyncio.QueueFull):
                self.responses.put_nowait((payload, address[0]))


def parse_router(payload: bytes, location: str, address: str, local_address: str) -> RouterService:
    if len(payload) > 65536 or b"<!" in payload:
        raise ValueError("invalid router description")
    document = ET.fromstring(payload)
    for service in document.iter():
        if service.tag.rsplit("}", 1)[-1] != "service":
            continue
        fields = {child.tag.rsplit("}", 1)[-1]: child.text or "" for child in service}
        service_type = fields.get("serviceType", "")
        if service_type not in (
            "urn:schemas-upnp-org:service:WANIPConnection:1",
            "urn:schemas-upnp-org:service:WANIPConnection:2",
            "urn:schemas-upnp-org:service:WANPPPConnection:1",
        ):
            continue
        control_url = urljoin(location, fields.get("controlURL", ""))
        parts = urlsplit(control_url)
        if (
            parts.scheme == "http"
            and parts.hostname == address
            and not (parts.username or parts.password or parts.fragment)
        ):
            return RouterService(address, control_url, service_type, local_address)
    raise ValueError("router has no supported IGD service")


async def discover_router(local_address: str) -> RouterService | None:
    if not is_router_address(local_address):
        return None
    protocol = _Discovery()
    transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
        lambda: protocol, local_addr=(local_address, 0)
    )
    try:
        transport.sendto(
            b"M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
            b'MAN: "ssdp:discover"\r\nMX: 1\r\n'
            b"ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\r\n",
            ("239.255.255.250", 1900),
        )
        async with asyncio.timeout(2):
            for _attempt in range(4):
                payload, address = await protocol.responses.get()
                fields = {
                    name.strip().lower(): value.strip()
                    for line in payload.decode("iso-8859-1").split("\r\n")
                    if ":" in line
                    for name, value in [line.split(":", 1)]
                }
                location = fields.get("location", "")
                try:
                    description = await fetch_router(location, address)
                    return parse_router(description, location, address, local_address)
                except (OSError, ValueError, ET.ParseError, asyncio.IncompleteReadError):
                    continue
    except TimeoutError:
        return None
    finally:
        transport.close()
    return None
