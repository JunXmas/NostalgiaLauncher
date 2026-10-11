"""Own-game LAN host mode never falls back to an unrelated multicast world."""

from __future__ import annotations

import pytest
from test_lan_probe import status_server
from test_service import LoopThread, wait_for

from nostalgia.multiplayer.lan_output import lan_port_from_output
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.service import RoomService


@pytest.mark.parametrize(
    "line, port",
    [
        ("[Server thread/INFO]: Started serving on 51234", 51234),
        ("Started serving on port 65535", 65535),
        ("[Render thread/INFO]: [System] [CHAT] Local game hosted on port 1024", 1024),
        ("\x1b[32m[Server thread/INFO]: Started serving on 51234\x1b[0m", 51234),
        ("[Server thread/INFO] [minecraft/IntegratedServer]: Started serving on 54321", 54321),
        ("[CHAT] <guest> Started serving on 54321", 0),
        ("[Render thread/INFO]: [CHAT] <guest> Local game hosted on port 54321", 0),
        ("Started serving on 22", 0),
        ("Started serving on 65536", 0),
        ("Started serving on 512345", 0),
        ("Connecting to 51234", 0),
    ],
)
def test_lan_stdout_announcements(line: str, port: int) -> None:
    assert lan_port_from_output(line) == port


def test_managed_host_probes_supplied_port_and_ignores_beacons() -> None:
    remote = LoopThread()
    statuses: list[RoomStatus] = []
    failures: list[str] = []
    detections: list[float] = []

    def unexpected_detector(timeout: float) -> None:
        detections.append(timeout)
        raise AssertionError("must not choose another local world")

    service = RoomService(
        remote.relay.url,
        on_status=statuses.append,
        on_failure=failures.append,
        detect_world=unexpected_detector,
        relay_enabled=True,
    )
    try:
        service.start_hosting(auto_detect=False)
        wait_for(lambda: bool(statuses) and statuses[-1].role == "waiting_world")
        with status_server(False) as port:
            service.supply_lan_port(port).result(3)
            wait_for(lambda: bool(failures))
        assert statuses[-1].role == "waiting_world"
        with status_server() as port:
            service.supply_lan_port(port).result(3)
            wait_for(lambda: statuses[-1].role == "hosting")
        assert not detections and len(failures) == 1
        service.stop().result(3)
        assert [status.role for status in statuses][-1] == "idle"
    finally:
        service.shutdown()
        remote.close()
