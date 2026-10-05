"""Mã phòng: đủ entropy, tách đúng, và KHÔNG nhận mã ngắn bỏ secret (luật L6)."""

from __future__ import annotations

import pytest

from nostalgia.errors import MultiplayerError
from nostalgia.multiplayer.room_code import (
    ALPHABET,
    ROOM_CODE_LENGTH,
    make_room_code,
    normalise_room_code,
    split_room_code,
)


def test_room_code_has_entropy() -> None:
    codes = {make_room_code() for _ in range(200)}
    assert len(codes) == 200
    assert all(len(code) == ROOM_CODE_LENGTH and set(code) <= set(ALPHABET) for code in codes)
    assert not set("0O1IL") & set(ALPHABET)
    assert len(ALPHABET) ** (ROOM_CODE_LENGTH - 6) > 2**58


def test_split_tolerates_user_formatting() -> None:
    room_code = make_room_code()
    spaced = f" {room_code[:6].lower()}-{room_code[6:12]} {room_code[12:]}\n"
    assert normalise_room_code(spaced) == room_code
    room_id, room_secret = split_room_code(spaced)
    assert (room_id, room_secret) == (room_code[:6], room_code[6:])


@pytest.mark.parametrize("bad", ["ABCDEF", "", "ABCDEF" * 3 + "A", "ABCDEFGHJKMN0PQRST"])
def test_short_or_foreign_codes_are_rejected(bad: str) -> None:
    with pytest.raises(MultiplayerError, match="mã phòng"):
        split_room_code(bad)
