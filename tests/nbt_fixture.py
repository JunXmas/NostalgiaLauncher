"""Dựng `level.dat` giả (NBT nén gzip) cho test bộ đọc NBT và ô CHƠI TIẾP, không cần Minecraft.

Cấu trúc theo đúng game: compound gốc tên rỗng → compound `Data` chứa `LevelName` (string) và
`LastPlayed` (long) cùng các tag nhiễu đủ loại (list, mảng, compound lồng) để bộ đọc phải nhảy
qua đúng cách.
"""

from __future__ import annotations

import gzip
import struct
from pathlib import Path

TAG_BYTE, TAG_INT, TAG_LONG, TAG_DOUBLE, TAG_BYTE_ARRAY, TAG_STRING = 1, 3, 4, 6, 7, 8
TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 9, 10, 11, 12


def _string(text: str) -> bytes:
    raw = text.encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


def _named(tag_id: int, name: str, payload: bytes) -> bytes:
    return bytes([tag_id]) + _string(name) + payload


def _compound(children: bytes) -> bytes:
    return children + b"\x00"


def _noise_tags(nested_depth: int) -> bytes:
    """Các tag có thật trong level.dat mà bộ đọc phải bỏ qua."""
    player = _compound(_named(TAG_STRING, "name", _string("Jun")))
    noise = _named(TAG_INT, "GameType", struct.pack(">i", 0))
    noise += _named(TAG_BYTE, "hardcore", b"\x00")
    noise += _named(TAG_DOUBLE, "BorderSize", struct.pack(">d", 6.0e7))
    noise += _named(TAG_INT_ARRAY, "Ids", struct.pack(">i", 3) + struct.pack(">iii", 1, 2, 3))
    noise += _named(TAG_LONG_ARRAY, "Longs", struct.pack(">i", 2) + struct.pack(">qq", 5, 6))
    noise += _named(TAG_BYTE_ARRAY, "Bytes", struct.pack(">i", 2) + b"\x01\x02")
    noise += _named(TAG_LIST, "Players", bytes([TAG_COMPOUND]) + struct.pack(">i", 2) + player * 2)
    nested = _named(TAG_STRING, "doDaylightCycle", _string("true"))
    for _ in range(nested_depth):
        nested = _named(TAG_COMPOUND, "GameRules", _compound(nested))
    return noise + nested


def build_level_dat(
    world_name: str, last_played_ms: int, *, nested_depth: int = 2, noise: bool = True
) -> bytes:
    children = _named(TAG_STRING, "LevelName", _string(world_name))
    children += _named(TAG_LONG, "LastPlayed", struct.pack(">q", last_played_ms))
    if noise:
        children += _noise_tags(nested_depth)
    top = _named(TAG_COMPOUND, "", _compound(_named(TAG_COMPOUND, "Data", _compound(children))))
    return gzip.compress(top)


def deeply_nested_level(depth: int) -> bytes:
    """`Data` chứa `depth` compound lồng nhau — để kiểm trần độ sâu của bộ đọc."""
    inner = _named(TAG_STRING, "LevelName", _string("Sâu"))
    for _ in range(depth):
        inner = _named(TAG_COMPOUND, "X", _compound(inner))
    return gzip.compress(
        _named(TAG_COMPOUND, "", _compound(_named(TAG_COMPOUND, "Data", _compound(inner))))
    )


def write_world(game_dir: Path, folder: str, world_name: str, last_played_ms: int) -> Path:
    level_path = game_dir / "saves" / folder / "level.dat"
    level_path.parent.mkdir(parents=True, exist_ok=True)
    level_path.write_bytes(build_level_dat(world_name, last_played_ms))
    return level_path
