"""Luật L3 (chỉ tin beacon từ loopback, cổng hợp lệ) và L9 (kiểm Sec-WebSocket-Accept)."""

from __future__ import annotations

import asyncio
import socket
import sys
import threading
import time

import pytest
from fake_relay import FakeRelay

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.bridge import JoinerBridge
from nostalgia.multiplayer.lan import (
    MULTICAST_GROUP,
    MULTICAST_PORT,
    LanWorld,
    _interface_ipv4_addresses,
    build_beacon,
    detect_open_to_lan,
    is_local_peer,
    parse_lan_beacon,
)
from nostalgia.net.websocket import MAX_FRAME_BYTES, WebSocketClient

# Chụp `connect` thật ở thời điểm import module — TRƯỚC khi fixture autouse `no_accidental_internet`
# (tests/conftest.py) vá nó cho từng test. `_interface_ipv4_addresses_via_udp_connect()` cần
# `connect()` thật tới một địa chỉ không phải loopback để kernel chọn route qua NIC thật (không
# gói UDP nào thật sự rời máy trong bước `connect()`), việc mà lưới chặn mạng của bộ test cấm
# theo mặc định.
_REAL_SOCKET_CONNECT = socket.socket.connect


def test_lan_detect_ignores_non_loopback_source() -> None:
    beacon = build_beacon(25565, "Thế giới của Jun")
    found = parse_lan_beacon(beacon, "127.0.0.1")
    assert found is not None and (found.world_port, found.world_name) == (25565, "Thế giới của Jun")
    assert parse_lan_beacon(beacon, "192.168.1.7") is None  # máy khác trong LAN
    assert parse_lan_beacon(beacon, "::1") is None  # IPv6 không dùng cho multicast v4
    # Minecraft phát qua card LAN nên nguồn là IP LAN của CHÍNH máy này: phải nhận.
    mine = frozenset({"127.0.0.1", "192.168.1.17"})
    assert parse_lan_beacon(beacon, "192.168.1.17", mine) is not None
    assert parse_lan_beacon(beacon, "192.168.1.7", mine) is None


@pytest.mark.parametrize("bad_port", [22, 0, 1023, 65536, 99999])
def test_lan_detect_rejects_bad_port(bad_port: int) -> None:
    assert parse_lan_beacon(build_beacon(bad_port, "x"), "127.0.0.1") is None
    assert parse_lan_beacon(b"[MOTD]x[/MOTD]", "127.0.0.1") is None


def test_detect_open_to_lan_finds_real_beacon_over_loopback() -> None:
    """Dò THẬT (không chỉ hàm thuần): phát beacon giả qua loopback, khẳng định
    `detect_open_to_lan()` mở socket, join multicast, nghe, và trả đúng world.

    Máy chạy CI/dev có thể có launcher/agent khác cũng đang phát beacon thật trên cùng cổng
    4445 (cổng multicast cố định theo giao thức Minecraft, không đổi được) — `detect_open_to_lan`
    trả world ĐẦU TIÊN thấy được, có thể là beacon của tiến trình khác. Vòng lặp dưới đây lặp
    gọi/phát tới khi thấy ĐÚNG world của chính test, giống cách `service.py._wait_for_world`
    polling thật, thay vì giả định lần gọi đầu tiên chắc chắn là của mình.
    """
    world_name = f"Beacon giả trong test {time.monotonic_ns()}"
    beacon = build_beacon(25566, world_name)
    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
    sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton("127.0.0.1"))

    found: LanWorld | None = None
    deadline = time.monotonic() + 15.0
    try:
        while found is None and time.monotonic() < deadline:
            result: dict[str, object] = {}

            def detect(result: dict[str, object] = result) -> None:
                result["world"] = detect_open_to_lan(1.0)

            detector = threading.Thread(target=detect)
            detector.start()
            resend_deadline = time.monotonic() + 1.0
            while detector.is_alive() and time.monotonic() < resend_deadline:
                sender.sendto(beacon, (MULTICAST_GROUP, MULTICAST_PORT))
                time.sleep(0.1)
            detector.join(2.0)
            assert not detector.is_alive(), "detect_open_to_lan() không trả về đúng hạn"
            candidate = result.get("world")
            if candidate is not None and candidate.world_name == world_name:  # type: ignore[attr-defined]
                found = candidate  # type: ignore[assignment]
    finally:
        sender.close()

    assert found is not None, "None trong khi beacon đang phát là lỗi"
    assert (found.world_port, found.world_name) == (25566, world_name)


def test_detect_open_to_lan_bind_failure_differs_from_timeout() -> None:
    """Bind hỏng (cổng bị chiếm bởi socket không chia sẻ được) phải ném `MultiplayerError`
    kèm errno — KHÁC với hết giờ không thấy beacon, vốn trả `None` im lặng."""
    blocker = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    blocker.bind(("", MULTICAST_PORT))  # không SO_REUSEADDR/REUSEPORT: chiếm cổng độc quyền
    try:
        with pytest.raises(MultiplayerError, match=r"errno=") as excinfo:
            detect_open_to_lan(0.2)
        assert "4445" in str(excinfo.value)
    finally:
        blocker.close()

    # Gỡ chướng ngại: bind lại thành công, không còn ném MultiplayerError. Không khẳng định
    # cứng None — máy dev có thể đang chạy launcher thật (nghe đúng cổng 4445) và phát beacon
    # thật đúng lúc; kết quả hợp lệ ở đây là "không ném MultiplayerError", bất kể trả None hay
    # một LanWorld thật.
    try:
        detect_open_to_lan(0.2)
    except MultiplayerError as exc:
        pytest.fail(f"bind lại phải thành công sau khi gỡ chướng ngại, nhưng vẫn lỗi: {exc}")


def test_interface_addresses_fallback_without_fcntl(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows không có `fcntl`: `_interface_ipv4_addresses()` phải rơi về kỹ thuật UDP
    `connect()` + `getsockname()` thay vì trả rỗng (nguyên nhân (1) trong JL-13)."""
    monkeypatch.setattr(socket.socket, "connect", _REAL_SOCKET_CONNECT)
    monkeypatch.setitem(
        sys.modules, "fcntl", None
    )  # `import fcntl` bên trong hàm sẽ ném ImportError

    addresses = _interface_ipv4_addresses()

    assert addresses, "fallback không có fcntl vẫn phải tìm được ít nhất một IP của máy"
    for address in addresses:
        socket.inet_aton(address)  # phải là IPv4 hợp lệ
    assert "127.0.0.1" not in addresses, "fallback phải tìm IP NIC thật, không phải loopback"


def test_websocket_accept_is_verified() -> None:
    async def scenario() -> None:
        async def bad_server(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            while (await reader.readline()) not in (b"\r\n", b""):
                pass
            writer.write(
                b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                b"Sec-WebSocket-Accept: bogus=\r\n\r\n"
            )
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(bad_server, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        with pytest.raises(MultiplayerError, match="Sec-WebSocket-Accept"):
            await WebSocketClient.connect(f"ws://127.0.0.1:{port}/s/ABC?role=join")
        server.close()
        await server.wait_closed()

    asyncio.run(scenario())


def test_frame_caps() -> None:
    async def scenario() -> None:
        relay = FakeRelay()
        await relay.start()
        host = await WebSocketClient.connect(f"{relay.url}/s/ROOM01?role=host")
        joiner = await WebSocketClient.connect(f"{relay.url}/s/ROOM01?role=join")
        opened = await host.receive()
        assert opened[4] == 1  # OPEN
        await joiner.send(b"x" * 70000)  # hơn 65535: khung 64-bit, vẫn dưới trần
        assert len(await host.receive()) == 70000 + 5
        room = relay.rooms["ROOM01"]
        assert room.host is not None
        await room.host.send(b"y" * (MAX_FRAME_BYTES + 1))  # relay lỗi/độc: vượt trần → đóng
        assert await host.receive() == b""
        assert host.closed
        await joiner.close()
        await relay.stop()

    asyncio.run(scenario())


def test_is_local_peer_accepts_this_machine_and_rejects_neighbours() -> None:
    """Nửa "từ chối" của luật L7 mới: proxy nghe mọi interface nên PHẢI phân biệt được
    kết nối của chính máy này (loopback, IP card LAN) với hàng xóm cùng LAN."""
    local = frozenset({"127.0.0.1", "192.168.1.17"})
    assert is_local_peer("127.0.0.1", local)
    assert is_local_peer("127.0.53.1", local)
    assert is_local_peer("192.168.1.17", local)
    assert not is_local_peer("192.168.1.44", local), "hàng xóm cùng LAN phải bị đóng cửa"
    assert not is_local_peer("", local)


def test_bridge_serve_slams_the_door_on_foreign_peers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chốt cửa phải NỐI DÂY trong `_serve` và đóng TRƯỚC khi mở gì tới relay: giả một peer
    lạ bằng cách vá `is_local_peer` (test thật không thể nối từ IP của máy khác)."""

    async def scenario() -> None:
        relay = FakeRelay()
        await relay.start()
        joiner = JoinerBridge(relay.url, "ROOM02", "S" * 12)
        await joiner.start()
        monkeypatch.setattr("nostalgia.multiplayer.bridge.is_local_peer", lambda *_: False)
        reader, writer = await asyncio.open_connection("127.0.0.1", joiner.local_port)
        assert await asyncio.wait_for(reader.read(1), 3) == b"", "peer lạ phải bị đóng ngay"
        assert "ROOM02" not in relay.rooms, "bị từ chối thì không được chạm tới relay"
        writer.close()
        await joiner.stop()
        await relay.stop()

    asyncio.run(scenario())
