"""Bố cục bạn bè trên cửa sổ nhỏ giữ chỗ soạn tin và nút quay lại."""

from typing import Any

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_social_ui import find_control, login_preview
from test_social_ui import social_preview as social_preview

from qt_controls import press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("scale", [100, 150])
def test_small_view_switches_list_and_chat_without_stale_draft(
    social_preview: tuple[Any, ...],
    scale: int,
) -> None:
    _, _, view, root_item, social, _, _, _ = social_preview
    login_preview(social_preview)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, False, True, "vi"
    )
    view.resize(1024, 600)
    QTest.qWait(60)
    rail = find_control(root_item, "friendsRail")
    chat = find_control(root_item, "friendChat")
    assert rail.isVisible() and not chat.isVisible()
    press(view, find_control(root_item, "friend-misa"))
    wait_until(lambda: social.peerId == "misa" and not social.busy)
    assert chat.isVisible() and not rail.isVisible()
    page = find_control(root_item, "friendsPage")
    assert 0 <= chat.mapToItem(page, QPointF()).x() <= 5
    composer = find_control(root_item, "chatComposer")
    origin = composer.mapToItem(page, QPointF())
    assert origin.y() >= 0 and origin.y() + composer.height() <= page.height()
    find_control(root_item, "chatComposer").setProperty("text", "Bản nháp riêng")
    press(view, find_control(root_item, "backToFriends"))
    assert rail.isVisible() and not chat.isVisible()
    press(view, find_control(root_item, "friend-misa"))
    assert find_control(root_item, "chatComposer").property("text") == ""
    assert not find_control(root_item, "friendCodeInput").isVisible()
    press(view, find_control(root_item, "backToFriends"))
    press(view, find_control(root_item, "showAddFriend"))
    assert find_control(root_item, "friendCodeInput").isVisible()
