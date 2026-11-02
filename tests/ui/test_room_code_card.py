"""Mã phòng ngay trên trang Bạn bè: khách nhập mã + Vào, chủ phòng thấy mã + Chép."""

from typing import Any

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import RoomStatus
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_guest_joins_with_typed_code_through_room_service(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, view, root_item, _, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    joined: list[str] = []
    monkeypatch.setattr(multiplayer._service, "join", joined.append)
    code_input = find_control(root_item, "roomCodeInput")
    join = find_control(root_item, "joinRoomCode")
    assert code_input.isVisible() and join.isVisible()
    assert not find_control(root_item, "hostRoomCode").isVisible()
    code_input.setCode("abcdef-abc")
    assert not join.property("clickable")
    code_input.setCode("abcdef-abcdef ghjkmn")
    assert code_input.property("code") == "ABCDEFABCDEFGHJKMN"
    assert join.property("clickable")
    sync_bridge.set_host_ready(False)
    assert not join.property("clickable")
    sync_bridge.set_host_ready(True)
    press(view, join)
    wait_until(lambda: joined == ["ABCDEFABCDEFGHJKMN"])
    # Đang ở phòng thì ô nhập mã nhường chỗ cho nút xem phòng; bấm thêm không vào lần hai.
    multiplayer._apply_status(RoomStatus(role="joined", local_port=51234))
    QTest.qWait(40)
    assert not code_input.isVisible() and find_control(root_item, "showActiveRoom").isVisible()
    sync_bridge.join("ABCDEFABCDEFGHJKMN")
    assert joined == ["ABCDEFABCDEFGHJKMN"]


def test_paste_fills_the_three_boxes(social_preview: tuple[Any, ...]) -> None:
    _, _, view, root_item, *_ = social_preview
    login_preview(social_preview)
    QGuiApplication.clipboard().setText("  abcdef abcdef ghjkmn ")
    press(view, find_control(root_item, "pasteRoomCode"))
    assert find_control(root_item, "roomCodeInput").property("code") == "ABCDEFABCDEFGHJKMN"
    assert find_control(root_item, "joinRoomCode").property("clickable")


def test_host_sees_spaced_code_and_copies_it(social_preview: tuple[Any, ...]) -> None:
    _, _, view, root_item, _, multiplayer, *_ = social_preview
    login_preview(social_preview)
    page = find_control(root_item, "friendsPage")
    multiplayer._apply_status(
        RoomStatus(role="hosting", room_code="ABCDEFABCDEFGHJKMN", host_ticket="ticket")
    )
    QTest.qWait(40)
    for section in (0, 1):
        page.setProperty("section", section)
        QTest.qWait(40)
        shown = find_control(root_item, "hostRoomCode")
        assert shown.isVisible() and shown.property("text") == "ABCDEF ABCDEF GHJKMN"
        assert not find_control(root_item, "roomCodeInput").isVisible()
    QGuiApplication.clipboard().setText("")
    press(view, find_control(root_item, "copyRoomCode"))
    assert QGuiApplication.clipboard().text() == "ABCDEFABCDEFGHJKMN"
