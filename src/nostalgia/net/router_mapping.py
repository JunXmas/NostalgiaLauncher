"""Ánh xạ UDP của launcher trên IGD; lease ngắn và thu hồi khi đóng kết nối."""

from __future__ import annotations

import asyncio
import contextlib
import ipaddress
import secrets
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from xml.sax.saxutils import escape

from nostalgia.net.router_discovery import RouterService
from nostalgia.net.router_http import fetch_router

ROUTER_LEASE_SECONDS = 300


@dataclass(frozen=True, slots=True)
class RouterMapping:
    service: RouterService
    external_address: str
    external_port: int
    local_port: int
    description: str


class RouterFault(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__("router SOAP fault: " + code)
        self.code = code


async def _soap(service: RouterService, action: str, arguments: dict[str, str]) -> bytes:
    fields = "".join(f"<{name}>{escape(value)}</{name}>" for name, value in arguments.items())
    body = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f'<s:Body><u:{action} xmlns:u="{service.service_type}">{fields}</u:{action}>'
        "</s:Body></s:Envelope>"
    ).encode()
    payload = await fetch_router(
        service.control_url,
        service.address,
        body=body,
        action=service.service_type + "#" + action,
        allow_fault=True,
    )
    if len(payload) > 65536 or b"<!" in payload:
        raise ValueError("invalid router SOAP response")
    document = ET.fromstring(payload)
    for child in document.iter():
        if child.tag.rsplit("}", 1)[-1] == "errorCode":
            raise RouterFault(child.text or "unknown")
    return payload


def _port_arguments(port: int) -> dict[str, str]:
    return {"NewRemoteHost": "", "NewExternalPort": str(port), "NewProtocol": "UDP"}


async def _mapping_owner(mapping: RouterMapping) -> bool:
    try:
        payload = await _soap(
            mapping.service, "GetSpecificPortMappingEntry", _port_arguments(mapping.external_port)
        )
    except RouterFault as exc:
        if exc.code == "714":
            return False
        raise
    fields = {
        child.tag.rsplit("}", 1)[-1]: child.text or "" for child in ET.fromstring(payload).iter()
    }
    return (
        fields.get("NewInternalClient") == mapping.service.local_address
        and fields.get("NewInternalPort") == str(mapping.local_port)
        and fields.get("NewPortMappingDescription") == mapping.description
    )


async def create_mapping(service: RouterService, local_port: int) -> RouterMapping:
    if not 1 <= local_port <= 65535:
        raise ValueError("invalid local ICE port")
    payload = await _soap(service, "GetExternalIPAddress", {})
    if len(payload) > 65536 or b"<!" in payload:
        raise ValueError("invalid external address response")
    document = ET.fromstring(payload)
    address = next(
        (
            child.text or ""
            for child in document.iter()
            if child.tag.endswith("NewExternalIPAddress")
        ),
        "",
    )
    external = ipaddress.IPv4Address(address)
    if not external.is_global:
        raise ValueError("router has no public IPv4 address")
    try:
        await _soap(service, "GetSpecificPortMappingEntry", _port_arguments(local_port))
    except RouterFault as exc:
        if exc.code != "714":
            raise
    else:
        raise ValueError("router port already mapped")
    mapping = RouterMapping(
        service, address, local_port, local_port, "Nostalgia " + secrets.token_hex(8)
    )
    try:
        await _add_mapping(mapping)
    except BaseException:
        with contextlib.suppress(OSError, ValueError, TimeoutError):
            await asyncio.shield(remove_mapping(mapping))
        raise
    return mapping


async def _add_mapping(mapping: RouterMapping) -> None:
    await _soap(
        mapping.service,
        "AddPortMapping",
        {
            **_port_arguments(mapping.external_port),
            "NewInternalPort": str(mapping.local_port),
            "NewInternalClient": mapping.service.local_address,
            "NewEnabled": "1",
            "NewPortMappingDescription": mapping.description,
            "NewLeaseDuration": str(ROUTER_LEASE_SECONDS),
        },
    )


async def renew_mapping(mapping: RouterMapping) -> None:
    if not await _mapping_owner(mapping):
        raise ValueError("router mapping ownership changed")
    await _add_mapping(mapping)


async def remove_mapping(mapping: RouterMapping) -> None:
    if await _mapping_owner(mapping):
        await _soap(mapping.service, "DeletePortMapping", _port_arguments(mapping.external_port))
