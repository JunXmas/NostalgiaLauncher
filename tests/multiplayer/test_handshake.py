"""Bắt tay thuần: dựng/đọc khung, HMAC đúng miền, sai secret hay replay thì không khớp."""

from __future__ import annotations

import pytest

from nostalgia.multiplayer import handshake as hs


def test_frame_round_trip_with_trailing_bytes() -> None:
    frame = hs.build_frame(hs.CHALLENGE, b"nonce-bytes", b"\x00" * 32) + b"minecraft"
    parsed = hs.parse_frame(frame)
    assert parsed is not None
    assert (parsed.op, parsed.fields, parsed.trailing) == (
        hs.CHALLENGE,
        (b"nonce-bytes", b"\x00" * 32),
        b"minecraft",
    )


def test_partial_frame_waits_and_garbage_fails_fast() -> None:
    frame = hs.build_hello(hs.make_nonce())
    for cut in range(1, len(frame)):
        assert hs.parse_frame(frame[:cut]) is None
    with pytest.raises(ValueError):
        hs.parse_frame(b"\x10\x00")  # gói Minecraft thẳng, chưa bắt tay
    with pytest.raises(ValueError):
        hs.parse_frame(b"NLh1\x05abcde")  # phiên bản cũ: không có fallback


def test_mutual_proofs_verify_and_reject_wrong_secret() -> None:
    join_nonce, host_nonce = hs.make_nonce(), hs.make_nonce()
    challenge = hs.parse_frame(hs.build_challenge("SECRET", join_nonce, host_nonce))
    assert challenge is not None and challenge.fields[0] == host_nonce
    assert hs.proof_matches(hs.prove("SECRET", b"host", join_nonce), challenge.fields[1])
    assert not hs.proof_matches(hs.prove("WRONG", b"host", join_nonce), challenge.fields[1])
    # Miền tách: proof của host không dùng lại được làm proof của joiner (phản xạ).
    assert not hs.proof_matches(hs.prove("SECRET", b"join", join_nonce), challenge.fields[1])
    response = hs.parse_frame(hs.build_response("SECRET", host_nonce))
    assert response is not None
    assert hs.proof_matches(hs.prove("SECRET", b"join", host_nonce), response.fields[0])


def test_nonces_differ_so_a_captured_proof_cannot_be_replayed() -> None:
    first, second = hs.make_nonce(), hs.make_nonce()
    assert first != second and len(first) == hs.NONCE_LENGTH
    old_proof = hs.prove("SECRET", b"join", first)
    assert not hs.proof_matches(hs.prove("SECRET", b"join", second), old_proof)
