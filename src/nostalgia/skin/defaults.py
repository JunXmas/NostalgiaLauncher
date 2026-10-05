"""Skin mặc định Steve/Alex, chọn theo UUID đúng như Java (`uuid.hashCode() & 1`)."""

from __future__ import annotations

import uuid as uuid_module
from importlib.resources import files
from pathlib import Path

from nostalgia.skin.model import PlayerSkin


def is_alex(player_uuid: str) -> bool:
    """Java: `(hash & 1) == 1` → Alex, với hash = xor bốn nhóm 32 bit của UUID."""
    value = uuid_module.UUID(player_uuid).int
    parts = [(value >> shift) & 0xFFFFFFFF for shift in (96, 64, 32, 0)]
    return (parts[0] ^ parts[1] ^ parts[2] ^ parts[3]) & 1 == 1


def default_skin(player_uuid: str) -> PlayerSkin:
    slim = is_alex(player_uuid)
    resource = files("nostalgia.skin") / "defaults" / ("alex.png" if slim else "steve.png")
    return PlayerSkin(skin_path=Path(str(resource)), slim=slim)
