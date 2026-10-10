"""Hướng dẫn mời world hiện ngay từ chat, có GIF offline và đủ bước ở cả hai ngôn ngữ."""

from typing import Any

import pytest
from PySide6.QtQuick import QQuickItem
from test_bridges import wait_until
from test_social_ui import find_control, login_preview
from test_social_ui import social_preview as social_preview

from qt_controls import find_control as find_popup
from qt_controls import press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("language", ["vi", "en"])
def test_chat_opens_world_invitation_guide_with_lan_and_guest_steps(
    social_preview: tuple[Any, ...], language: str
) -> None:
    _, gateway, view, root_item, social, *_rest = social_preview
    login_preview(social_preview)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        100, False, False, False, language
    )
    social.selectFriend("misa")
    wait_until(lambda: not social.busy)
    chat = find_control(root_item, "friendChat")
    press(view, find_control(chat, "guideButton-invite"))
    dialog = find_popup(root_item, "guideDialog")
    wait_until(lambda: dialog.property("opened"))
    assert dialog.property("topicId") == "invite"
    topic = dialog.property("topic").toVariant()
    steps = " ".join(topic["steps"])
    assert "Open to LAN" in steps and "Start LAN World" in steps
    assert (
        ("Tạo phòng" in steps and "Khởi chạy & vào world" in steps)
        if language == "vi"
        else ("Create room" in steps and "Launch & join world" in steps)
    )
    wait_until(lambda: find_popup(root_item, "guideMedia").property("ready"))
    assert (
        find_popup(root_item, "guideAnimation").property("source").toString().endswith("host.gif")
    )
    assert not gateway.invited
    dialog.close()


@pytest.mark.parametrize("scale", [100, 150])
def test_single_create_entry_stays_visible_when_a_friend_is_selected(
    social_preview: tuple[Any, ...],
    scale: int,
) -> None:
    _, gateway, view, root_item, social, *_rest = social_preview
    login_preview(social_preview)
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, False, True, "vi"
    )
    social.selectFriend("misa")
    wait_until(lambda: not social.busy)
    assert not find_control(root_item, "inviteSelectedFriend").isVisible()
    button = find_control(root_item, "friendsOpenRoom")
    assert button.isVisible() and button.property("label") == "Tạo phòng"
    assert button.property("clickable")
    page = find_control(root_item, "friendsPage")
    for section in (0, 1):
        page.setProperty("section", section)
        create_buttons = [
            control
            for control in page.findChildren(QQuickItem)
            if control.isVisible() and control.property("label") == "Tạo phòng"
        ]
        assert create_buttons == [button]
    press(view, button)
    dialog = find_popup(root_item, "hostDialog")
    wait_until(lambda: dialog.property("opened"))
    dialog.close()
    assert not gateway.invited
