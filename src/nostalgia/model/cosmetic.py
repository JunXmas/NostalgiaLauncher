"""Dữ liệu rig cosmetic dùng chung, không đọc đĩa hoặc gọi mạng."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CosmeticNode:
    parent_index: int
    translation: tuple[float, ...]
    rotation: tuple[float, ...]
    vertices: tuple[float, ...]
    keys: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class CosmeticPart:
    bone: str
    duration: float
    nodes: tuple[CosmeticNode, ...]


@dataclass(frozen=True, slots=True)
class CosmeticAsset:
    texture_png: bytes
    parts: tuple[CosmeticPart, ...]
