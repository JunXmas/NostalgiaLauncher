"""Bắt tay xác thực hai chiều trên mỗi stream, THUẦN: chỉ dựng và đọc byte.

    joiner → host : HELLO(join_nonce)
    host → joiner : CHALLENGE(host_nonce, host_proof = HMAC(secret, "host" + join_nonce))
    joiner → host : RESPONSE(join_proof = HMAC(secret, "join" + host_nonce))

Secret không bao giờ lên dây; hai bên chỉ chứng minh giữ nó trên nonce của bên kia (chống
replay), tách miền host/join (chống phản xạ). Chỉ có phiên bản này — không fallback (luật L1).

Khung: MAGIC | op(1) | field_count(1) | (len(1) + bytes)* — mỗi field ≤ 255 byte.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass

MAGIC = b"NLh2"
HELLO, CHALLENGE, RESPONSE = 1, 2, 3
NONCE_LENGTH = 18  # 144 bit mỗi phía
MAX_HANDSHAKE_BYTES = 512  # bộ đệm chờ đủ khung; hơn là rác hoặc tấn công
HANDSHAKE_TIMEOUT_SECONDS = 8.0


@dataclass(frozen=True, slots=True)
class HandshakeFrame:
    op: int
    fields: tuple[bytes, ...]
    trailing: bytes  # byte đã tới sau khung — của Minecraft, chuyển tiếp sau khi xác thực


def make_nonce() -> bytes:
    return secrets.token_bytes(NONCE_LENGTH)


def prove(room_secret: str, domain: bytes, nonce: bytes) -> bytes:
    """HMAC-SHA256(secret, domain + nonce)."""
    return hmac.new(room_secret.encode("utf-8"), domain + nonce, hashlib.sha256).digest()


def proof_matches(expected: bytes, presented: bytes) -> bool:
    return hmac.compare_digest(expected, presented)


def build_frame(op: int, *fields: bytes) -> bytes:
    body = bytearray(MAGIC)
    body.append(op & 0xFF)
    body.append(len(fields) & 0xFF)
    for field in fields:
        clipped = field[:255]
        body.append(len(clipped))
        body += clipped
    return bytes(body)


def parse_frame(buffer: bytes) -> HandshakeFrame | None:
    """`None` = chưa đủ byte, cứ chờ. Ném `ValueError` khi byte không phải khung bắt tay."""
    head = min(len(buffer), len(MAGIC))
    if buffer[:head] != MAGIC[:head]:
        raise ValueError("không phải khung bắt tay")
    if len(buffer) < len(MAGIC) + 2:
        return None
    op, count = buffer[4], buffer[5]
    position = 6
    fields: list[bytes] = []
    for _ in range(count):
        if len(buffer) < position + 1:
            return None
        length = buffer[position]
        position += 1
        if len(buffer) < position + length:
            return None
        fields.append(bytes(buffer[position : position + length]))
        position += length
    return HandshakeFrame(op, tuple(fields), bytes(buffer[position:]))


def build_hello(join_nonce: bytes) -> bytes:
    return build_frame(HELLO, join_nonce)


def build_challenge(room_secret: str, join_nonce: bytes, host_nonce: bytes) -> bytes:
    return build_frame(CHALLENGE, host_nonce, prove(room_secret, b"host", join_nonce))


def build_response(room_secret: str, host_nonce: bytes) -> bytes:
    return build_frame(RESPONSE, prove(room_secret, b"join", host_nonce))
