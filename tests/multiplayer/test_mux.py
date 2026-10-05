"""Khung mux và phép kiểm gói Handshake Minecraft (luật L4)."""

from __future__ import annotations

from nostalgia.multiplayer.mux import (
    CLOSE,
    DATA,
    looks_like_minecraft_handshake,
    pack_mux_frame,
    unpack_mux_frame,
)


def test_mux_frame_round_trip() -> None:
    assert unpack_mux_frame(pack_mux_frame(7, DATA, b"abc")) == (7, DATA, b"abc")
    assert unpack_mux_frame(pack_mux_frame(2**32 - 1, CLOSE)) == (2**32 - 1, CLOSE, b"")
    assert unpack_mux_frame(b"\x00\x00\x01") is None


def test_first_bytes_must_be_minecraft_handshake() -> None:
    # length=16, id=0, protocol=763 (1.20.1), "localhost", port 25565, next_state=2
    packet = bytes([0x10, 0x00, 0xFB, 0x05, 0x09]) + b"localhost" + b"\x63\xdd\x02"
    assert looks_like_minecraft_handshake(packet) is True
    assert looks_like_minecraft_handshake(packet[:1]) is None
    assert (
        looks_like_minecraft_handshake(b"GET / HTTP/1.1\r\n") is False
    )  # 'G'=0x47 length 71, id 'E'
    assert looks_like_minecraft_handshake(b"\x10\x01" + b"x" * 15) is False  # packet id ≠ 0
    assert looks_like_minecraft_handshake(b"\xff\xff\xff\xff\x7f") is False  # length khổng lồ
    assert looks_like_minecraft_handshake(b"\x00\x00") is False
