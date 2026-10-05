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
import logging
import re
import socket
import struct
import sys
import time
from dataclasses import dataclass

from nostalgia.errors import MultiplayerError

logger = logging.getLogger(__name__)

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
    """Mọi IPv4 của máy này: loopback, địa chỉ theo hostname, và từng card mạng (ioctl trên
    Linux/macOS, hoặc UDP connect()+getsockname() trên Windows — không gói nào rời máy, nên
    chạy được cả dưới lưới chặn mạng của bộ test khi nguồn là loopback/mạng nội bộ)."""
    found = {"127.0.0.1"}
    with contextlib.suppress(OSError):
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            found.add(str(info[4][0]))
    found.update(_interface_ipv4_addresses())
    return frozenset(found)


def _interface_ipv4_addresses() -> set[str]:
    try:
        import fcntl  # chỉ có trên POSIX
    except ImportError:
        return _interface_ipv4_addresses_via_udp_connect()
    request_address = 0x8915 if sys.platform.startswith("linux") else 0xC0206921  # SIOCGIFADDR
    found: set[str] = set()
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with probe:
        for _, interface_name in socket.if_nameindex():
            packed = struct.pack("256s", interface_name.encode()[:15])
            with contextlib.suppress(OSError):
                reply = fcntl.ioctl(probe.fileno(), request_address, packed)
                found.add(socket.inet_ntoa(reply[20:24]))
    return found


def _interface_ipv4_addresses_via_udp_connect() -> set[str]:
    """Windows: không có `fcntl`/`SIOCGIFADDR`. `connect()` UDP không gửi gói nào lên dây —
    chỉ nhờ kernel chọn route rồi đọc `getsockname()` ra IP của NIC sẽ dùng để ra ngoài.
    Chỉ lấy được IP của interface trên route mặc định (không liệt kê hết mọi NIC), nhưng đủ để
    `parse_lan_beacon` nhận ra beacon Minecraft phát từ chính máy này qua card đó."""
    found: set[str] = set()
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with probe, contextlib.suppress(OSError):
        probe.connect(("192.0.2.1", 80))  # RFC5737 TEST-NET-1: không gói nào thật sự gửi đi
        found.add(probe.getsockname()[0])
    return found


def is_local_peer(peer_host: str, local_hosts: frozenset[str]) -> bool:
    """Kết nối TCP này có phải từ CHÍNH máy này không (loopback hoặc IP của một card mạng).

    Minecraft nối tới `<IP nguồn beacon>:<port>` — và nguồn của beacon multicast là IP card
    LAN (192.168.x), không phải 127.0.0.1, vì Java join nhóm trên card theo route mặc định.
    Nên proxy joiner phải nhận kết nối đến qua IP LAN của chính máy; hàng xóm cùng LAN nối
    vào thì peer là IP CỦA HỌ → đóng. Giả nguồn TCP qua LAN cần đoạt được bắt tay ba bước —
    không nằm trong mô hình đe doạ của một launcher (luật L7, docs/MULTIPLAYER_SECURITY.md)."""
    return peer_host.startswith("127.") or peer_host in local_hosts


def parse_lan_beacon(
    datagram: bytes, source_host: str, local_hosts: frozenset[str] = frozenset({"127.0.0.1"})
) -> LanWorld | None:
    """Thuần. `None` nếu không phải beacon Minecraft, nguồn không phải máy này, cổng vô lý."""
    if not (source_host.startswith("127.") or source_host in local_hosts):
        return None
    port_matches = _PORT_TAG.findall(datagram)
    if not port_matches:
        return None
    world_port = int(port_matches[-1])
    if not 1024 <= world_port <= 65535:
        return None
    motd_match = _MOTD_TAG.search(datagram)
    world_name = motd_match.group(1).decode("utf-8", "replace") if motd_match else "World"
    # Lọc bỏ mọi thẻ đặc biệt khỏi tên thế giới để ngăn injection qua MOTD.
    sanitised_name = _PORT_TAG.sub(b"", world_name.encode("utf-8", "replace")).decode(
        "utf-8", "replace"
    )
    return LanWorld(world_port, sanitised_name[:64])


def detect_open_to_lan(timeout_seconds: float) -> LanWorld | None:
    """Chặn tới `timeout_seconds`; trả world đầu tiên hợp lệ. Gọi từ luồng nền.

    Bind/join hỏng là một BƯỚC CHẾT (interface sai, cổng bị chiếm bởi tiến trình khác không
    chia sẻ được...): log `warning` và ném `MultiplayerError`. Hết giờ mà không thấy beacon là
    tình huống bình thường (chưa ai mở "Open to LAN"): trả `None`, không log gì.
    """
    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # Minecraft của host cũng nghe 4445 → cần REUSEPORT để cùng nghe.
    if hasattr(socket, "SO_REUSEPORT"):
        with contextlib.suppress(OSError):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    try:
        listener.bind(("", MULTICAST_PORT))
    except OSError as exc:
        listener.close()
        logger.warning("không bind được cổng dò LAN %d: %s", MULTICAST_PORT, exc)
        raise MultiplayerError(
            f"không mở được cổng dò LAN {MULTICAST_PORT}: {exc} (errno={exc.errno})"
        ) from exc

    local_hosts = local_ipv4_addresses()
    group_bytes = socket.inet_aton(MULTICAST_GROUP)
    joined = 0
    # INADDR_ANY một mình để routing table chọn card — máy nhiều NIC (Wifi+Ethernet+vEthernet)
    # dễ join nhầm. Join lặp trên TỪNG IP cục bộ để không bỏ sót card nào.
    for host in sorted(local_hosts):
        try:
            interface_bytes = socket.inet_aton(host)
        except OSError:
            continue  # không phải IPv4 hợp lệ (không nên xảy ra, nhưng đừng chết vì nó)
        membership = struct.pack("4s4s", group_bytes, interface_bytes)
        try:
            listener.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
            joined += 1
        except OSError as exc:
            # Một interface lỗi trong khi các cái khác còn join được: không phải bước chết.
            logger.debug("không join multicast LAN qua %s: %s", host, exc)
    if joined == 0:
        listener.close()
        logger.warning(
            "không join được nhóm multicast LAN trên interface nào (%d ứng viên: %s)",
            len(local_hosts),
            sorted(local_hosts),
        )
        raise MultiplayerError(
            f"không join được nhóm multicast LAN {MULTICAST_GROUP} trên interface nào"
        )

    deadline = time.monotonic() + timeout_seconds
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
    """Phát beacon giả để Minecraft trên CÙNG máy thấy world trong tab LAN.

    Không tin loopback luôn nhận làm interface multicast (Windows thường không nhận):
    `IP_MULTICAST_IF` đặt lần lượt theo từng IP cục bộ và gửi qua tất cả, thay vì im lặng đi
    sai card khi loopback hỏng.
    """
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
    beacon = build_beacon(local_port, world_name)
    interfaces = sorted(local_ipv4_addresses())
    try:
        while True:
            sent = False
            for host in interfaces:
                try:
                    sender.setsockopt(
                        socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(host)
                    )
                    sender.sendto(beacon, (MULTICAST_GROUP, MULTICAST_PORT))
                    sent = True
                except OSError as exc:
                    logger.debug("không phát beacon LAN giả qua %s: %s", host, exc)
            if not sent:
                logger.warning(
                    "không phát được beacon LAN giả qua interface nào (%d ứng viên)",
                    len(interfaces),
                )
            await asyncio.sleep(ANNOUNCE_INTERVAL_SECONDS)
    finally:
        sender.close()
