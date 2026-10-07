"""Read the LAN announcement from the selected game's own stdout, not nearby beacons."""

from __future__ import annotations

import re

_LAN_PORT = re.compile(
    r"(?:^|\]:\s+)(?:Started serving on(?: port)?|"
    r"(?:\[System\]\s*)?(?:\[CHAT\]\s*)?Local game hosted on port)"
    r"\s+(\d{4,5})\.?\s*$"
)


def lan_port_from_output(line: str) -> int:
    match = _LAN_PORT.search(line)
    if match is None:
        return 0
    port = int(match[1])
    return port if 1024 <= port <= 65535 else 0
