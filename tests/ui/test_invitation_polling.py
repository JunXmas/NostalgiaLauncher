"""Lời mời vẫn hoạt động khi polling, không vượt qua trạng thái host hoặc phiên mới."""

from threading import Event
from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_social_ui import find_control, login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import RoomStatus
from nostalgia.errors import SessionRevoked, SocialError

pytestmark = pytest.mark.usefixtures("qt_app")


def ready_host(multiplayer: Any) -> None:
    multiplayer._apply_status(
        RoomStatus(
            role="hosting",
            room_code="ABCDEFABCDEFGHJKMN",
            host_ticket="opaque-ticket",
            world_name="World",
        )
    )


@pytest.mark.parametrize("action", ["send", "accept", "decline"])
def test_invitation_actions_work_during_poll_and_ignore_duplicate_clicks(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    _, gateway, view, root_item, social, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    if action == "send":
        social.selectFriend("misa")
        wait_until(lambda: not social.busy)
    social._timer.stop()
    poll_started, poll_release, action_started, action_release = Event(), Event(), Event(), Event()
    method = {"send": "send_invite", "accept": "accept_invite", "decline": "decline_invite"}[action]
    original = getattr(gateway, method)
    calls: list[str] = []
    joined: list[str] = []
    monkeypatch.setattr(sync_bridge, "join", joined.append)

    def poll() -> Any:
        snapshot = gateway.snapshot
        poll_started.set()
        assert poll_release.wait(10)
        return snapshot

    def perform(*args: Any) -> Any:
        calls.append(action)
        action_started.set()
        assert action_release.wait(10)
        return original(*args)

    monkeypatch.setattr(gateway, "fetch_snapshot", poll)
    monkeypatch.setattr(gateway, method, perform)
    if action == "send":
        ready_host(multiplayer)
    try:
        social.refresh()
        wait_until(poll_started.is_set)
        name = {
            "send": "inviteSelectedFriend",
            "accept": "acceptInvite-invite",
            "decline": "declineInvite-invite",
        }[action]
        button = find_control(root_item, name)
        assert button.isVisible() and button.property("clickable")
        center = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)
        wait_until(action_started.is_set)
        assert social.busy and social.inviteBusy and not button.property("clickable")
        {
            "send": social.inviteFriend,
            "accept": social.acceptInvite,
            "decline": social.declineInvite,
        }[action]("misa" if action == "send" else "invite")
        action_release.set()
        wait_until(lambda: not social.inviteBusy)
        assert calls == [action]
        assert joined == (["ABCDEFABCDEFGHJKMN"] if action == "accept" else [])
        poll_release.set()
        wait_until(lambda: not social.busy)
        if action != "send":
            wait_until(lambda: not social.invitations)
    finally:
        poll_release.set()
        action_release.set()
        wait_until(lambda: not social.busy and not social.inviteBusy)


@pytest.mark.parametrize("revoked", [False, True])
def test_invitation_error_never_joins_and_revoked_session_is_removed(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, revoked: bool
) -> None:
    _, gateway, _view, _root_item, social, _multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    social._timer.stop()
    joined: list[str] = []
    monkeypatch.setattr(sync_bridge, "join", joined.append)

    def fail(_invite_id: str) -> str:
        raise SessionRevoked("Phiên bị thu hồi.") if revoked else SocialError("Lời mời hết hạn.")

    monkeypatch.setattr(gateway, "accept_invite", fail)
    social.acceptInvite("invite")
    wait_until(lambda: not social.inviteBusy)
    assert not joined
    assert social.signedIn is not revoked
    assert not gateway.access_token if revoked else social.invitations
    assert social.note == ("Phiên bị thu hồi." if revoked else "Lời mời hết hạn.")


@pytest.mark.parametrize("change", ["session", "host"])
def test_delayed_accept_cannot_join_after_session_or_room_changes(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    _, gateway, _view, _root_item, social, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    social._timer.stop()
    started, release = Event(), Event()
    joined: list[str] = []
    monkeypatch.setattr(sync_bridge, "join", joined.append)

    def delayed(_invite_id: str) -> str:
        started.set()
        assert release.wait(10)
        return "ABCDEFABCDEFGHJKMN"

    monkeypatch.setattr(gateway, "accept_invite", delayed)
    try:
        social.acceptInvite("invite")
        wait_until(started.is_set)
        if change == "session":
            social._reset_session("Phiên mới")
            gateway.access_token = "new-token"
        else:
            ready_host(multiplayer)
        release.set()
        wait_until(lambda: not social.inviteBusy and not social.busy)
        assert not joined
        if change == "session":
            assert social.note == "Phiên mới" and gateway.access_token == "new-token"
    finally:
        release.set()
        wait_until(lambda: not social.inviteBusy)


def test_waiting_lan_and_unpublished_pack_cannot_send_invites(
    social_preview: tuple[Any, ...],
) -> None:
    _, gateway, _view, _root_item, social, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    multiplayer._apply_status(RoomStatus(role="waiting_world"))
    social.inviteFriend("misa")
    ready_host(multiplayer)
    sync_bridge.set_host_ready(False)
    social.inviteFriend("misa")
    sync_bridge.set_host_ready(True)
    social.inviteFriend("stranger")
    assert not social.inviteBusy and not gateway.invited
