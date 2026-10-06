"""Mã phòng không có trong envelope và chỉ máy nhận đúng khóa/phòng giải được."""

from __future__ import annotations

import json

import pytest

from nostalgia.errors import SocialError
from nostalgia.social.envelope import InvitationCipher


def test_invitation_only_recipient_decrypts_and_context_is_bound() -> None:
    recipient = InvitationCipher()
    stranger = InvitationCipher()
    room_code = "ABCDEFABCDEFGHJKMN"
    envelope = stranger.encrypt(room_code, "guest", recipient.public_key)
    document = {"room_id": "ABCDEF", "recipient_key": recipient.public_key, "envelope": envelope}
    assert room_code not in json.dumps(envelope)
    assert recipient.decrypt(document, "guest") == room_code
    with pytest.raises(SocialError):
        stranger.decrypt(document, "guest")
    with pytest.raises(SocialError):
        recipient.decrypt(document, "someone-else")
    document["room_id"] = "ABCDEG"
    with pytest.raises(SocialError):
        recipient.decrypt(document, "guest")
