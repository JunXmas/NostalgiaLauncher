"""Mời một cú bấm từ danh sách bạn bè; lời mời đến hiện ở trang Bạn bè với nút Vào phòng."""

from dataclasses import replace
from typing import Any

import pytest
from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_invitation_polling import ready_host
from test_social_ui import find_control, login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.social.model import Friend

pytestmark = pytest.mark.usefixtures("qt_app")


def click(view: Any, control: Any) -> None:
    QTest.qWait(60)
    center = control.mapToScene(QPointF(control.width() / 2, control.height() / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)


def test_every_friend_gets_one_click_invite_while_hosting(
    social_preview: tuple[Any, ...],
) -> None:
    _, gateway, view, root_item, social, multiplayer, sync_bridge, _ = social_preview
    gateway.snapshot = replace(
        gateway.snapshot, invitations=(), friends=(*gateway.snapshot.friends, Friend("ha", "Hà"))
    )
    login_preview(social_preview)
    invite = find_control(root_item, "inviteFriend-ha")
    assert not invite.isVisible()
    ready_host(multiplayer)
    wait_until(
        lambda: invite.isVisible() and find_control(root_item, "inviteFriend-misa").isVisible()
    )
    profile_dialog = root_item.findChild(QObject, "socialProfileDialog")
    click(view, invite)
    wait_until(lambda: gateway.invited == ["ha"] and not social.inviteBusy)
    # Nút Mời nằm trong hàng mở hồ sơ: bấm Mời không được mở hồ sơ.
    QTest.qWait(150)
    assert not profile_dialog.property("visible")
    status = multiplayer.room_snapshot()
    multiplayer._apply_status(replace(status, locked=True))
    assert not invite.isVisible()
    multiplayer._apply_status(status)
    sync_bridge.set_host_ready(False)
    assert not invite.isVisible()
    sync_bridge.set_host_ready(True)
    multiplayer.stop()
    multiplayer._apply_status(replace(status, role="idle", room_code=""))
    assert not invite.isVisible()


def test_incoming_invitation_shows_join_on_friends_page(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, view, root_item, social, _, sync_bridge, _ = social_preview
    login_preview(social_preview)
    joined: list[str] = []
    monkeypatch.setattr(sync_bridge, "join", joined.append)
    accept = find_control(root_item, "acceptInvite-invite")
    assert find_control(root_item, "friendsPage").property("section") == 0
    assert accept.isVisible() and accept.property("label") == "Vào phòng"
    click(view, accept)
    wait_until(lambda: joined == ["ABCDEFABCDEFGHJKMN"] and not social.inviteBusy)
    wait_until(lambda: not social.invitations and not social.busy)
