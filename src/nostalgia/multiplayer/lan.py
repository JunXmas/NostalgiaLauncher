"""Multicast "Open to LAN" của Minecraft: nghe (phía host) và phát giả (phía joiner).

Minecraft phát `[MOTD]<tên>[/MOTD][AD]<cổng>[/AD]` tới 224.0.2.60:4445 mỗi 1,5 s. Đây là
kênh CỤC BỘ mỗi máy; đường dữ liệu thật đi qua relay.

Luật L3: chỉ tin datagram có nguồn là địa chỉ CỦA CHÍNH MÁY NÀY (Minecraft phát multicast qua
card LAN nên nguồn là IP LAN, ví dụ 192.168.1.17, không phải 127.0.0.1), cổng trong 1024..65535.
Không thì hàng xóm cùng LAN phát `[AD]22[/AD]` là launcher-host bắc cầu relay tới ssh của mình.
"""

from __future__ import annotations

import asyncio
import contextlib
import re
import socket
import struct
import time
from dataclasses import dataclass

MULTICAST_GROUP = "224.0.2.60"
MULTICAST_PORT = 4445
ANNOUNCE_INTERVAL_SECONDS = 1.5
_PORT_TAG = re.compile(rb"\[AD\](\d{1,5})\[/AD\]")
_MOTD_TAG = re.compile(rb"\[MOTD\](.*?)\[/MOTD\]", re.S)


@dataclass(frozen=True, slots=True)
class LanWorld:
    world_port: int
    world_name: str


def local_ipv4_addresses() -> frozenset[str]:
    """Mọi IPv4 của máy này: loopback, địa chỉ theo hostname, và card đi ra multicast."""
    found = {"127.0.0.1"}
    with contextlib.suppress(OSError):
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(str(info[4][0]))
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with contextlib.suppress(OSError), probe:
        probe.connect((MULTICAST_GROUP, MULTICAST_PORT))  # UDP connect: không gửi gói nào
        found.add(str(probe.getsockname()[0]))
    return frozenset(found)


def parse_lan_beacon(
    datagram: bytes, source_host: str, local_hosts: frozenset[str] = frozenset({"127.0.0.1"})
) -> LanWorld | None:
    """Thuần. `None` nếu không phải beacon Minecraft, nguồn không phải máy này, cổng vô lý."""
    if not (source_host.startswith("127.") or source_host in local_hosts):
        return None
    port_match = _PORT_TAG.search(datagram)
    if port_match is None:
        return None
    world_port = int(port_match.group(1))
    if not 1024 <= world_port <= 65535:
        return None
    motd_match = _MOTD_TAG.search(datagram)
    world_name = motd_match.group(1).decode("utf-8", "replace") if motd_match else "World"
    return LanWorld(world_port, world_name[:64])


def detect_open_to_lan(timeout_seconds: float) -> LanWorld | None:
    """Chặn tới `timeout_seconds`; trả world đầu tiên hợp lệ. Gọi từ luồng nền."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Minecraft của host cũng nghe 4445 → cần REUSEPORT để cùng nghe.
    if hasattr(socket, "SO_REUSEPORT"):
        with contextlib.suppress(OSError):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    try:
        listener.bind(("", MULTICAST_PORT))
        membership = struct.pack("4sL", socket.inet_aton(MULTICAST_GROUP), socket.INADDR_ANY)
        listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    except OSError:
        listener.close()
        return None
    deadline = time.monotonic() + timeout_seconds
    local_hosts = local_ipv4_addresses()
    try:
        while (remaining := deadline - time.monotonic()) > 0:
            listener.settimeout(remaining)
            try:
                datagram, source = listener.recvfrom(1024)
            except TimeoutError:
                return None
            found = parse_lan_beacon(datagram, str(source[0]), local_hosts)
            if found is not None:
                return found
    finally:
        listener.close()
    return None


def build_beacon(local_port: int, world_name: str) -> bytes:
    return f"[MOTD]{world_name}[/MOTD][AD]{local_port}[/AD]".encode()


async def announce_forever(local_port: int, world_name: str) -> None:
    """Phát beacon giả qua loopback để Minecraft trên CÙNG máy thấy world trong tab LAN."""
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    with contextlib.suppress(OSError):
        sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("127.0.0.1"))
    beacon = build_beacon(local_port, world_name)
    try:
        while True:
            with contextlib.suppress(OSError):  # NIC rớt một nhịp: bỏ nhịp, không chết vòng
                sender.sendto(beacon, (MULTICAST_GROUP, MULTICAST_PORT))
            await asyncio.sleep(ANNOUNCE_INTERVAL_SECONDS)
    finally:
        sender.close()
