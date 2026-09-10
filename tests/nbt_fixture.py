"""Dựng `level.dat` giả (NBT nén gzip) cho test bộ đọc NBT và ô CHƠI TIẾP, không cần Minecraft.

Cấu trúc theo đúng game: compound gốc tên rỗng → compound `Data` chứa `LevelName` (string) và
`LastPlayed` (long) cùng các tag nhiễu đủ loại (list, mảng, compound lồng) để bộ đọc phải nhảy
qua đúng cách.
"""

from __future__ import annotations

import gzip
import struct
import zlib
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


# ----- servers.dat: NBT KHÔNG nén -----


def tiny_png(width: int = 64, height: int = 64) -> bytes:
    """PNG RGBA xanh lá hợp lệ, dựng bằng zlib/struct — icon server giả."""
    raw = b"".join(b"\x00" + bytes([40, 160, 60, 255]) * width for _ in range(height))

    def chunk(chunk_type: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def build_servers_dat(servers: list[tuple[str, str, str | None, bool]]) -> bytes:
    """`servers`: (name, ip, icon_base64 | None, hidden). Đúng dạng game ghi, thêm tag nhiễu."""
    elements = b""
    for server_name, address, icon_base64, hidden in servers:
        children = _named(TAG_STRING, "name", _string(server_name))
        children += _named(TAG_STRING, "ip", _string(address))
        children += _named(TAG_BYTE, "acceptTextures", b"\x01")
        if icon_base64 is not None:
            children += _named(TAG_STRING, "icon", _string(icon_base64))
        if hidden:
            children += _named(TAG_BYTE, "hidden", b"\x01")
        elements += _compound(children)
    servers_list = bytes([TAG_COMPOUND if servers else 0]) + struct.pack(">i", len(servers))
    return _named(TAG_COMPOUND, "", _compound(_named(TAG_LIST, "servers", servers_list + elements)))


def write_servers(game_dir: Path, servers: list[tuple[str, str, str | None, bool]]) -> Path:
    servers_path = game_dir / "servers.dat"
    servers_path.parent.mkdir(parents=True, exist_ok=True)
    servers_path.write_bytes(build_servers_dat(servers))
    return servers_path
