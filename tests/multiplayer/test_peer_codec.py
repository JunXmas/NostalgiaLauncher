"""SDP mã hoá không được chuyển sang phòng/mục đích khác hoặc sửa fingerprint."""

import pytest
from cryptography.exceptions import InvalidTag

from nostalgia.multiplayer.peer_codec import (
    PeerDescription,
    build_peer_envelope,
    parse_peer_envelope,
)


def test_encrypted_description_rejects_tampering_and_wrong_scope() -> None:
    description = PeerDescription(
        "v=0\r\nm=application 9 UDP/DTLS/SCTP webrtc-datachannel\r\na=fingerprint:sha-256 "
        + ":".join(["01"] * 32)
        + "\r\n",
        "offer",
    )
    encoded = build_peer_envelope("room-secret", "a" * 32, "game", description)
    assert "fingerprint" not in encoded
    assert parse_peer_envelope("room-secret", "a" * 32, "game", encoded) == description
    for secret, request_id, purpose in [
        ("other-room", "a" * 32, "game"),
        ("room-secret", "b" * 32, "game"),
        ("room-secret", "a" * 32, "sync"),
    ]:
        with pytest.raises(InvalidTag):
            parse_peer_envelope(secret, request_id, purpose, encoded)
    edited = encoded[:25] + ("A" if encoded[25] != "A" else "B") + encoded[26:]
    with pytest.raises(InvalidTag):
        parse_peer_envelope("room-secret", "a" * 32, "game", edited)
