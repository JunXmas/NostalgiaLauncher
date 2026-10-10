"""Cổng thủ công khôi phục luồng host khi multicast không dùng được, không mở SSH qua relay."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from test_service import LoopThread, wait_for

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.lan_probe import probe_lan_port
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService


@contextmanager
def status_server(valid: bool = True) -> Iterator[int]:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(3)
    payload = b'{"version":{"protocol":763},"players":{},"description":"World"}'
    response = (
        bytes([len(payload) + 2, 0, len(payload)]) + payload if valid else b"SSH-2.0-fixture\r\n"
    )

    def serve() -> None:
        try:
            connection, _ = listener.accept()
            with connection:
                connection.recv(1024)
                connection.sendall(response)
        except OSError:
            pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        listener.close()
        thread.join(3)


def test_actual_status_probe_and_non_minecraft_rejection() -> None:
    with status_server() as world_port:
        assert probe_lan_port(world_port).world_port == world_port
    with status_server(False) as world_port, pytest.raises(MultiplayerError):
        probe_lan_port(world_port)
    for world_port in (22, 80, 65536):
        with pytest.raises(MultiplayerError):
            probe_lan_port(world_port)


def test_manual_port_recovers_when_multicast_bind_fails() -> None:
    remote = LoopThread()
    statuses: list[RoomStatus] = []
    failures: list[str] = []

    def missing_multicast(_timeout: float) -> None:
        raise MultiplayerError("bind failed")

    service = RoomService(
        remote.relay.url,
        on_status=statuses.append,
        on_failure=failures.append,
        detect_world=missing_multicast,
        relay_enabled=True,
    )
    try:
        service.start_hosting()
        wait_for(lambda: bool(failures))
        assert statuses[-1].role == "waiting_world"
        with status_server() as world_port:
            service.supply_lan_port(world_port).result(3)
            wait_for(lambda: statuses[-1].role == "hosting")
        assert len(failures) == 1
    finally:
        service.shutdown()
        remote.close()


def test_stopping_waiting_world_cancels_probe_loop() -> None:
    remote = LoopThread()
    statuses: list[RoomStatus] = []

    def absent_world(_timeout: float) -> None:
        time.sleep(0.02)

    service = RoomService(
        remote.relay.url,
        on_status=statuses.append,
        on_failure=lambda _message: None,
        detect_world=absent_world,
        relay_enabled=True,
    )
    try:
        service.start_hosting()
        wait_for(lambda: bool(statuses) and statuses[-1].role == "waiting_world")
        service.stop().result(3)
        assert statuses[-1].role == "idle"
    finally:
        service.shutdown()
        remote.close()
