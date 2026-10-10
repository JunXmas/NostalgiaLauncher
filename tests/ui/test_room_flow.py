"""Luồng phòng thật: bước LAN, lời mời tại chỗ và địa chỉ khách không bị giấu."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_host_popup import host_popup as host_popup
from test_invitation_polling import ready_host
from test_minimal_preview import find_control, press
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import RoomStatus
from nostalgia.social.model import Friend

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("language", ["vi", "en"])
@pytest.mark.parametrize("scale", [100, 150])
def test_host_steps_and_invite_fit_and_follow_lan_and_pack_readiness(
    host_popup: tuple[Any, ...], language: str, scale: int, tmp_path: Path
) -> None:
    _, view, _, root_item, host, warnings = host_popup
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, False, True, language
    )
    multiplayer = view.rootContext().contextProperty("multiplayerBridge")
    sync_bridge = view.rootContext().contextProperty("roomSyncBridge")
    host.openSetup()
    popup = find_control(root_item, "hostDialog")
    wait_until(lambda: popup.property("opened"))
    page = find_control(root_item, "friendsPage")
    assert page.property("section") == 1
    popup.close()
    wait_until(lambda: not popup.property("visible"))
    host._instance_id, host._label = "a", "Cozy Adventures"
    host._stage_note("waiting_world", "Vào thế giới → Esc → Open to LAN → Start LAN World.")
    multiplayer._apply_status(RoomStatus(role="waiting_world"))
    QTest.qWait(80)
    steps = find_control(root_item, "hostRoomSteps")
    assert steps.property("currentStep") == 1
    assert find_control(root_item, "hostLanInstruction").isVisible()
    assert not find_control(root_item, "manualLanPort").isVisible()
    assert not find_control(root_item, "roomInviteArea").isVisible()
    assert view.grabWindow().save(str(tmp_path / f"room-lan-{language}-{scale}.png"))
    ready_host(multiplayer)
    sync_bridge.set_host_ready(False)
    host._stage_note("publishing", "Đang chuẩn bị phòng…")
    assert not find_control(root_item, "roomInviteArea").isVisible()
    sync_bridge.set_host_ready(True)
    host._stage_note("ready", "Phòng sẵn sàng.")
    QTest.qWait(80)
    assert steps.property("currentStep") == 2
    assert not find_control(root_item, "hostLanInstruction").isVisible()
    button = find_control(root_item, "roomInvite-misa")
    assert button.isVisible() and button.property("clickable")
    scroll = find_control(root_item, "friendsScroll")
    scroll.setProperty("contentY", scroll.property("maxY"))
    QTest.qWait(80)
    origin = button.mapToScene(QPointF())
    assert 0 <= origin.x() <= view.width() - button.width()
    assert 0 <= origin.y() <= view.height() - button.height()
    assert view.grabWindow().save(str(tmp_path / f"room-ready-{language}-{scale}.png"))
    assert not warnings


def test_invite_from_room_without_selecting_chat_and_lock_gates_it(
    social_preview: tuple[Any, ...],
) -> None:
    _, gateway, view, root_item, social, multiplayer, _, _ = social_preview
    login_preview(social_preview)
    find_control(root_item, "friendsPage").setProperty("section", 1)
    ready_host(multiplayer)
    QTest.qWait(80)
    button = find_control(root_item, "roomInvite-misa")
    assert not social.peerId and button.property("clickable")
    multiplayer._apply_status(replace(multiplayer.room_snapshot(), locked=True))
    assert not button.property("clickable")
    multiplayer._apply_status(replace(multiplayer.room_snapshot(), locked=False))
    center = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)
    wait_until(lambda: gateway.invited == ["misa"] and not social.inviteBusy)
    assert not social.peerId


def test_room_friend_list_is_virtualized_and_omits_offline_friends(
    social_preview: tuple[Any, ...],
) -> None:
    _, gateway, _, root_item, social, multiplayer, _, _ = social_preview
    login_preview(social_preview)
    social._timer.stop()
    gateway.snapshot = replace(
        gateway.snapshot,
        friends=tuple(Friend(f"friend-{n}", f"Friend {n}", n % 2 == 0) for n in range(1000)),
    )
    social.refresh()
    wait_until(lambda: len(social.friends) == 1000 and not social.busy)
    find_control(root_item, "friendsPage").setProperty("section", 1)
    ready_host(multiplayer)
    QTest.qWait(80)
    friends = find_control(root_item, "roomOnlineFriends")
    assert friends.property("count") == 500
    assert friends.property("height") <= 240
    delegates = [
        child
        for child in friends.property("contentItem").childItems()
        if child.property("modelData")
    ]
    assert 0 < len(delegates) < 20


def test_guest_can_copy_connection_address_without_opening_options(
    social_preview: tuple[Any, ...],
) -> None:
    _, _, view, root_item, _, multiplayer, _, _ = social_preview
    login_preview(social_preview)
    find_control(root_item, "friendsPage").setProperty("section", 1)
    multiplayer._apply_status(RoomStatus(role="joined", local_port=51234))
    QTest.qWait(80)
    button = find_control(root_item, "copyGuestRoomAddress")
    assert button.isVisible() and button.property("clickable")
    press(view, button)
    assert QGuiApplication.clipboard().text() == "127.0.0.1:51234"
