"""Mã phòng = `room_id` (relay thấy) + `room_secret` (khoá HMAC, không bao giờ lên dây).

Không có dạng mã ngắn "tương thích ngược": mã thiếu secret là mã sai (luật L6).
"""

from __future__ import annotations

import secrets

from nostalgia.errors import MultiplayerError

# Bỏ 0/O, 1/I/L để đọc qua điện thoại không nhầm. 31 ký tự.
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
ROOM_ID_LENGTH = 6
# 31^12 ≈ 2^59: dò qua relay bất khả thi, và relay còn rate-limit.
ROOM_SECRET_LENGTH = 12
ROOM_CODE_LENGTH = ROOM_ID_LENGTH + ROOM_SECRET_LENGTH


def make_room_code() -> str:
    """Mã mới cho mỗi lần host. `secrets.choice` phân bố đều trên bảng."""
    return "".join(secrets.choice(ALPHABET) for _ in range(ROOM_CODE_LENGTH))


def normalise_room_code(text: str) -> str:
    """Người dùng gõ hoặc dán: bỏ khoảng trắng và gạch, chữ hoa."""
    return "".join(character for character in text.upper() if character not in " -_\t\n")


def split_room_code(room_code: str) -> tuple[str, str]:
    """Tách (room_id, room_secret). Sai độ dài hoặc ký tự lạ → lỗi, không đoán."""
    normalised = normalise_room_code(room_code)
    if len(normalised) != ROOM_CODE_LENGTH or any(c not in ALPHABET for c in normalised):
        message = f"mã phòng phải có {ROOM_CODE_LENGTH} ký tự trong bảng {ALPHABET}"
        raise MultiplayerError(message)
    return normalised[:ROOM_ID_LENGTH], normalised[ROOM_ID_LENGTH:]
