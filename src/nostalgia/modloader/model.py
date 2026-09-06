"""Hình dạng chung của một bản mod loader, bất kể Fabric, Forge hay NeoForge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

LoaderKind = Literal["vanilla", "fabric", "quilt", "forge", "neoforge"]
LOADER_KINDS: tuple[LoaderKind, ...] = ("vanilla", "fabric", "quilt", "forge", "neoforge")

# Quilt chạy được mod Fabric; khi tìm mod cho bản Quilt thì nhận cả hai.
COMPATIBLE_LOADERS: dict[LoaderKind, tuple[str, ...]] = {
    "vanilla": (),
    "fabric": ("fabric",),
    "quilt": ("quilt", "fabric"),
    "forge": ("forge",),
    "neoforge": ("neoforge",),
}


def detect_loader_kind(version_id: str) -> LoaderKind:
    """Suy loader từ mã bản trong kho — quy ước tên của chính từng loader.

    Thứ tự quan trọng: `neoforge-21.1.9` chứa "forge", nên NeoForge phải xét trước Forge.
    """
    lowered = version_id.lower()
    if lowered.startswith("fabric-loader-"):
        return "fabric"
    if lowered.startswith("quilt-loader-"):
        return "quilt"
    if "neoforge" in lowered:
        return "neoforge"
    # `1.20.1-forge-47.4.10` (mới) và `1.7.10-Forge10.13.4.1614-1.7.10` (cũ, viết hoa, không gạch).
    if lowered.startswith("forge") or "-forge" in lowered:
        return "forge"
    return "vanilla"


@dataclass(frozen=True, slots=True)
class LoaderVersion:
    """Một bản loader dùng được với một phiên bản game.

    `stable`: Fabric đánh cờ `stable`; Forge là bản `recommended`; NeoForge là bản không
    mang hậu tố `-beta`. `installer_url` rỗng với Fabric (không cần installer).
    """

    loader_version: str
    stable: bool
    installer_url: str = ""
