"""Cổng LAN thủ công: chỉ nối loopback và kiểm phản hồi Minecraft Status trước relay."""

from __future__ import annotations

import json
import socket

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.lan import LanWorld


def _varint(value: int) -> bytes:
    encoded = bytearray()
    while True:
        current = value & 127
        value >>= 7
        encoded.append(current | (128 if value else 0))
        if not value:
            return bytes(encoded)


def _read_varint(connection: socket.socket) -> int:
    value = 0
    for shift in range(0, 35, 7):
        fragment = connection.recv(1)
        if not fragment:
            raise ValueError("unexpected EOF")
        value |= (fragment[0] & 127) << shift
        if fragment[0] < 128:
            return value
    raise ValueError("invalid VarInt")


def probe_lan_port(world_port: int) -> LanWorld:
    """Minecraft 1.7+; không quét cổng, không nối địa chỉ do người khác cung cấp."""
    if not 1024 <= world_port <= 65535:
        raise MultiplayerError("Cổng LAN phải nằm trong 1024 đến 65535.")
    try:
        with socket.create_connection(("127.0.0.1", world_port), timeout=1.5) as connection:
            address = b"localhost"
            handshake = (
                b"\x00"
                + _varint(763)
                + _varint(len(address))
                + address
                + world_port.to_bytes(2, "big")
                + b"\x01"
            )
            connection.sendall(_varint(len(handshake)) + handshake + b"\x01\x00")
            packet_size = _read_varint(connection)
            if not 2 <= packet_size <= 65536:
                raise ValueError("invalid packet size")
            payload = bytearray()
            while len(payload) < packet_size:
                fragment = connection.recv(packet_size - len(payload))
                if not fragment:
                    raise ValueError("unexpected EOF")
                payload.extend(fragment)
            if payload[0] != 0:
                raise ValueError("not a status packet")
            position, length = 1, 0
            for shift in range(0, 35, 7):
                current = payload[position]
                position += 1
                length |= (current & 127) << shift
                if current < 128:
                    break
            if length != len(payload) - position:
                raise ValueError("invalid JSON length")
            document = json.loads(payload[position:].decode())
            if (
                not isinstance(document, dict)
                or not isinstance(document.get("version"), dict)
                or not isinstance(document["version"].get("protocol"), int)
                or not isinstance(document.get("players"), dict)
                or "description" not in document
            ):
                raise ValueError("not Minecraft status")
    except (OSError, ValueError, IndexError, TypeError) as exc:
        raise MultiplayerError(
            "Không thấy Minecraft LAN ở cổng này. Hãy nhập cổng game báo sau khi mở LAN."
        ) from exc
    return LanWorld(world_port, "Minecraft LAN")
