"""Chat không bị polling khóa; kết quả gửi cũ không chạm tài khoản/khung chat mới."""

from dataclasses import replace
from threading import Event
from typing import Any

import pytest
from PySide6.QtTest import QSignalSpy
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.errors import SessionRevoked, SocialError
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_send_during_polling_to_offline_accepted_friend(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, gateway, view, root_item, social, *_rest = social_preview
    gateway.snapshot = replace(
        gateway.snapshot, friends=(replace(gateway.snapshot.friends[0], online=False),)
    )
    login_preview(social_preview)
    social.selectFriend("misa")
    wait_until(lambda: not social.busy and bool(social.messages))
    social._timer.stop()
    started, release = Event(), Event()
    original = gateway.fetch_snapshot

    def slow_snapshot() -> Any:
        started.set()
        assert release.wait(4)
        return original()

    monkeypatch.setattr(gateway, "fetch_snapshot", slow_snapshot)
    try:
        social.refresh()
        wait_until(started.is_set)
        assert social.busy and not social.peerOnline
        find_control(root_item, "chatComposer").setProperty("text", "Xin chào")
        send = find_control(root_item, "sendChat")
        assert send.property("clickable")
        press(view, send)
        wait_until(lambda: bool(gateway.sent) and not social.chatBusy)
        assert social.busy and gateway.sent == ["Xin chào"]
        assert find_control(root_item, "chatComposer").property("text") == ""
    finally:
        release.set()
        wait_until(lambda: not social.busy)


def test_unchanged_poll_does_not_rebuild_social_models(social_preview: tuple[Any, ...]) -> None:
    *_prefix, social, _multiplayer, _sync, _urls = social_preview
    login_preview(social_preview)
    social._timer.stop()
    spy = QSignalSpy(social.changed)
    social.refresh()
    wait_until(lambda: not social.busy)
    assert spy.count() == 0


@pytest.mark.parametrize("revoked", [False, True])
def test_send_failure_keeps_draft_or_revokes_session(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, revoked: bool
) -> None:
    _launcher, gateway, view, root_item, social, *_rest = social_preview
    login_preview(social_preview)
    social.selectFriend("misa")
    wait_until(lambda: not social.busy and bool(social.messages))
    social._timer.stop()

    def fail(*_args: Any) -> None:
        raise SessionRevoked("Phiên đã bị thu hồi.") if revoked else SocialError("Gửi thất bại.")

    monkeypatch.setattr(gateway, "send_message", fail)
    find_control(root_item, "chatComposer").setProperty("text", "Giữ bản nháp")
    press(view, find_control(root_item, "sendChat"))
    wait_until(lambda: not social.chatBusy)
    assert not gateway.sent
    if revoked:
        assert not social.signedIn and not gateway.access_token
    else:
        assert social.signedIn and social.note == "Gửi thất bại."
        assert find_control(root_item, "chatComposer").property("text") == "Giữ bản nháp"
