"""Accept stays usable during polling; failures and old sessions never accept in the UI."""

from dataclasses import replace
from threading import Event
from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.errors import SessionRevoked, SocialError
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


def test_accept_during_polling_and_double_click_sends_once(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, gateway, view, root_item, social, *_rest = social_preview
    login_preview(social_preview)
    social._timer.stop()
    started, poll_release, action_started, action_release = Event(), Event(), Event(), Event()
    original_accept = gateway.friend_action

    def slow_snapshot() -> Any:
        snapshot = gateway.snapshot
        started.set()
        assert poll_release.wait(5)
        return snapshot

    def slow_accept(action: str, account_id: str) -> None:
        action_started.set()
        assert action_release.wait(5)
        original_accept(action, account_id)

    monkeypatch.setattr(gateway, "fetch_snapshot", slow_snapshot)
    monkeypatch.setattr(gateway, "friend_action", slow_accept)
    try:
        social.refresh()
        wait_until(started.is_set)
        accept = find_control(root_item, "acceptFriend-minh")
        assert accept.isVisible() and accept.property("clickable")
        point = accept.mapToScene(QPointF(accept.width() / 2, accept.height() / 2)).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=point)
        wait_until(action_started.is_set)
        assert social.busy and social.friendBusy
        assert not accept.property("clickable")
        social.acceptFriend("minh")
        action_release.set()
        wait_until(lambda: not social.friendBusy)
        assert gateway.accepted == ["minh"]
        poll_release.set()
        wait_until(lambda: not social.busy and not social.requests)
    finally:
        poll_release.set()
        action_release.set()
        wait_until(lambda: not social.busy and not social.friendBusy)


@pytest.mark.parametrize("revoked", [False, True])
def test_friend_error_keeps_request_or_clears_revoked_session(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, revoked: bool
) -> None:
    _launcher, gateway, view, root_item, social, *_rest = social_preview
    login_preview(social_preview)
    social._timer.stop()

    def fail(*_args: Any) -> None:
        raise SessionRevoked("Phiên đã bị thu hồi.") if revoked else SocialError("Thử lại.")

    monkeypatch.setattr(gateway, "friend_action", fail)
    button = find_control(root_item, "acceptFriend-minh")
    center = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)
    wait_until(lambda: not social.friendBusy)
    assert not gateway.accepted
    if revoked:
        assert not social.signedIn and not gateway.access_token
    else:
        assert social.signedIn and social.note == "Thử lại."
        assert social.requests and button.property("clickable")


def test_old_friend_action_cannot_change_new_session(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, gateway, _view, _root_item, social, *_rest = social_preview
    login_preview(social_preview)
    social._timer.stop()
    started, release = Event(), Event()

    def slow_accept(*_args: Any) -> None:
        started.set()
        assert release.wait(5)

    monkeypatch.setattr(gateway, "friend_action", slow_accept)
    try:
        social.acceptFriend("minh")
        wait_until(started.is_set)
        social._reset_session("Phiên mới")
        gateway.access_token = "new-token"
        social._snapshot = replace(gateway.snapshot, requests=())
        release.set()
        wait_until(lambda: not social.friendBusy)
        assert social.signedIn and not social.requests and social.note == "Phiên mới"
        assert gateway.access_token == "new-token"
    finally:
        release.set()
        wait_until(lambda: not social.friendBusy)
