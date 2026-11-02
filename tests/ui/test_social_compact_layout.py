"""Bố cục bạn bè trên cửa sổ nhỏ: thẻ mã phòng và danh sách bạn nằm gọn trong trang."""

from typing import Any

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtTest import QTest
from test_social_ui import find_control, login_preview
from test_social_ui import social_preview as social_preview

from qt_controls import press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("scale", [100, 150])
def test_small_view_stacks_room_code_and_friend_list(
    social_preview: tuple[Any, ...],
    scale: int,
) -> None:
    _, _, view, root_item, _, _, _, _ = social_preview
    login_preview(social_preview)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, False, True, "vi"
    )
    view.resize(1024, 600)
    QTest.qWait(60)
    page = find_control(root_item, "friendsPage")
    for name in ("roomCodeCard", "friendsRail", "roomCodeInput"):
        panel = find_control(root_item, name)
        QTest.qWait(20)
        assert panel.isVisible() and panel.width() > 0, name
        origin = panel.mapToItem(page, QPointF())
        assert origin.x() >= 0 and origin.x() + panel.width() <= page.width() + 0.5, name
    assert not find_control(root_item, "friendCodeInput").isVisible()
    press(view, find_control(root_item, "showAddFriend"))
    assert find_control(root_item, "friendCodeInput").isVisible()
