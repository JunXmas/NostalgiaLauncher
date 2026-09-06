"""Hình dạng chung của một bản mod loader, bất kể Fabric, Forge hay NeoForge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LoaderKind = Literal["vanilla", "fabric", "forge", "neoforge"]
LOADER_KINDS: tuple[LoaderKind, ...] = ("vanilla", "fabric", "forge", "neoforge")


@dataclass(frozen=True, slots=True)
class LoaderVersion:
    """Một bản loader dùng được với một phiên bản game.

    `stable`: Fabric đánh cờ `stable`; Forge là bản `recommended`; NeoForge là bản không
    mang hậu tố `-beta`. `installer_url` rỗng với Fabric (không cần installer).
    """

    loader_version: str
    stable: bool
    installer_url: str = ""
