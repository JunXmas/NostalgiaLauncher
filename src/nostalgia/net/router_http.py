"""HTTP giới hạn cho router UPnP trong mạng riêng; không theo chuyển hướng."""

from __future__ import annotations

import asyncio
import ipaddress
from urllib.parse import urlsplit

MAX_ROUTER_BODY = 64 * 1024


def is_router_address(address: str) -> bool:
    try:
        parsed = ipaddress.IPv4Address(address)
        return parsed.is_private and not (
            parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_reserved
            or parsed.is_unspecified
        )
    except ipaddress.AddressValueError:
        return False


async def fetch_router(
    url: str, router_address: str, *, body: bytes = b"", action: str = "", allow_fault: bool = False
) -> bytes:
    parts = urlsplit(url)
    if (
        parts.scheme != "http"
        or parts.hostname != router_address
        or not is_router_address(router_address)
        or parts.username
        or parts.password
        or parts.fragment
        or any(character in url for character in "\r\n")
    ):
        raise ValueError("invalid router URL")
    port = parts.port or 80
    target = parts.path or "/"
    if parts.query:
        target += "?" + parts.query
    headers = (
        f"{'POST' if action else 'GET'} {target} HTTP/1.1\r\n"
        f"Host: {router_address}:{port}\r\nConnection: close\r\n"
    )
    if action:
        if any(character in action for character in '\r\n"'):
            raise ValueError("invalid SOAP action")
        headers += (
            f'SOAPAction: "{action}"\r\nContent-Type: text/xml; charset="utf-8"\r\n'
            f"Content-Length: {len(body)}\r\n"
        )
    async with asyncio.timeout(2):
        reader, writer = await asyncio.open_connection(router_address, port, limit=8192)
        try:
            writer.write(headers.encode("ascii") + b"\r\n" + body)
            await writer.drain()
            head = (await reader.readuntil(b"\r\n\r\n")).decode("iso-8859-1")
            status = head.split("\r\n", 1)[0].split(" ")[1]
            if status != "200" and not (allow_fault and status == "500"):
                raise ValueError("router request rejected")
            fields = {
                name.strip().lower(): value.strip()
                for line in head.split("\r\n")[1:]
                if ":" in line
                for name, value in [line.split(":", 1)]
            }
            if "transfer-encoding" in fields:
                raise ValueError("unsupported router transfer encoding")
            length = int(fields.get("content-length", "-1"))
            if not 0 <= length <= MAX_ROUTER_BODY:
                raise ValueError("invalid router response size")
            return await reader.readexactly(length)
        finally:
            writer.close()
            await writer.wait_closed()
