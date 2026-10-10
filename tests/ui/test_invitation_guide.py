"""Hướng dẫn mời world hiện ngay từ chat, có GIF offline và đủ bước ở cả hai ngôn ngữ."""

from typing import Any

import pytest
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
        ("Tạo room" in steps and "Khởi chạy & vào world" in steps)
        if language == "vi"
        else ("Create room" in steps and "Launch & join world" in steps)
    )
    wait_until(lambda: find_popup(root_item, "guideMedia").property("ready"))
    assert (
        find_popup(root_item, "guideAnimation").property("source").toString().endswith("host.gif")
    )
    assert not gateway.invited
    dialog.close()


def test_invite_entry_opens_host_selection_before_world_is_ready(
    social_preview: tuple[Any, ...],
) -> None:
    _, gateway, view, root_item, social, *_rest = social_preview
    login_preview(social_preview)
    social.selectFriend("misa")
    wait_until(lambda: not social.busy)
    button = find_control(root_item, "inviteSelectedFriend")
    assert button.property("label") == "Mở phòng" and button.property("clickable")
    press(view, button)
    dialog = find_popup(root_item, "hostDialog")
    wait_until(lambda: dialog.property("opened"))
    dialog.close()
    assert not gateway.invited
