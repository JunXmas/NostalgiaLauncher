"""Khung ghép kênh trên WebSocket của host, và phép kiểm "byte đầu là gói Minecraft" (luật L4).

Khung: [stream_id:4 big-endian][flag:1][payload]. flag 0 DATA, 1 OPEN (joiner mới), 2 CLOSE.
Relay chỉ bọc/mở khung này; nội dung payload là byte TCP thô của Minecraft.
"""

from __future__ import annotations

import struct

DATA, OPEN, CLOSE = 0, 1, 2
HEADER = struct.Struct("!IB")
# Gói Handshake của Minecraft: VarInt length, VarInt packet id 0, VarInt protocol, string
# address (≤255 ký tự), u16 port, VarInt next_state (1 status / 2 login / 3 transfer).
MAX_HANDSHAKE_PACKET = 300


def pack_mux_frame(stream_id: int, flag: int, payload: bytes = b"") -> bytes:
    return HEADER.pack(stream_id, flag) + payload


def unpack_mux_frame(frame: bytes) -> tuple[int, int, bytes] | None:
    """`None` nếu khung ngắn hơn phần đầu — relay lỗi, bỏ qua thay vì ném."""
    if len(frame) < HEADER.size:
        return None
    stream_id, flag = HEADER.unpack_from(frame)
    return stream_id, flag, frame[HEADER.size :]


def _read_varint(payload_bytes: bytes, position: int) -> tuple[int, int] | None:
    value, shift = 0, 0
    while shift < 35:
        if position >= len(payload_bytes):
            return None
        byte = payload_bytes[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, position
        shift += 7
    return None


def looks_like_minecraft_handshake(payload_bytes: bytes) -> bool | None:
    """`True` = gói Handshake hợp lệ, `False` = chắc chắn không phải, `None` = chưa đủ byte.

    Chỉ kiểm phần đầu để chặn byte rác của joiner đã qua xác thực nhưng không phải Minecraft;
    KHÔNG diễn giải gì sâu hơn — launcher chỉ chuyển tiếp byte.
    """
    length_read = _read_varint(payload_bytes, 0)
    if length_read is None:
        return None if len(payload_bytes) < 5 else False
    packet_length, position = length_read
    if not 5 <= packet_length <= MAX_HANDSHAKE_PACKET:
        return False
    if len(payload_bytes) < position + 1:
        return None
    return payload_bytes[position] == 0x00  # packet id của Handshake
