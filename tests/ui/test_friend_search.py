"""Tìm bạn cục bộ trong danh sách lớn; mời đúng người sau khi tái dùng hàng."""

from dataclasses import replace
from typing import Any

import pytest
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import RoomStatus
from nostalgia.social.model import Friend
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def count_rows(node: Any, prefix: str) -> int:
    return int(node.objectName().startswith(prefix)) + sum(
        count_rows(child, prefix) for child in node.childItems()
    )


def test_large_friend_list_search_normalizes_names_and_keeps_chat_idle(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, gateway, view, root_item, social, *_ = social_preview
    gateway.snapshot = replace(
        gateway.snapshot,
        invitations=(),
        friends=(
            *(Friend(str(i), f"Bạn {i:04d}", bool(i % 2)) for i in range(1999)),
            Friend("selected", "Đặng Nhật Minh", True),
        ),
    )
    login_preview(social_preview)
    social._timer.stop()
    calls: list[str] = []
    original = gateway.fetch_snapshot

    def snapshot() -> Any:
        calls.append("snapshot")
        return original()

    monkeypatch.setattr(gateway, "fetch_snapshot", snapshot)
    monkeypatch.setattr(gateway, "fetch_messages", lambda _account_id: calls.append("messages"))
    friends = find_control(root_item, "friendsList")
    search = find_control(root_item, "friendSearch")
    wait_until(lambda: friends.property("count") == 2000)
    QTest.qWait(80)
    assert count_rows(root_item, "friend-") < 40
    friends.scrollBy(float(friends.property("maxY")), True)
    wait_until(lambda: find_item(root_item, "friend-selected") is not None)
    search.setProperty("text", "  DANG nhat  ")
    wait_until(lambda: friends.property("count") == 1)
    assert abs(friends.property("contentY") - friends.property("originY")) < 1
    assert not calls
    press(view, find_control(root_item, "friend-selected"))
    wait_until(lambda: social.peerId == "selected" and not social.busy)
    assert "messages" not in calls
    calls.clear()
    search.setProperty("text", "không tồn tại")
    wait_until(lambda: friends.property("count") == 0)
    assert find_control(root_item, "friendSearchEmpty").property("visible")
    press(view, find_control(root_item, "friendSearchClear"))
    wait_until(lambda: friends.property("count") == 2000)
    assert search.property("text") == "" and not calls
    assert count_rows(root_item, "friend-") < 40


def test_room_search_only_invites_matching_online_friend_after_refresh(
    social_preview: tuple[Any, ...],
) -> None:
    _, gateway, view, root_item, social, multiplayer, *_ = social_preview
    gateway.snapshot = replace(
        gateway.snapshot,
        invitations=(),
        friends=(
            *(Friend(str(i), f"Bạn {i:04d}", True) for i in range(1000)),
            Friend("online", "Ngọc Ánh", True),
            Friend("offline", "Ngọc Ánh", False),
        ),
    )
    login_preview(social_preview)
    social._timer.stop()
    multiplayer._apply_status(
        RoomStatus(
            role="hosting",
            room_code="ABCDEFABCDEFGHJKMN",
            host_ticket="opaque-ticket",
            world_name="World",
        )
    )
    find_control(root_item, "friendsPage").setProperty("section", 1)
    friends = find_control(root_item, "roomOnlineFriends")
    search = find_control(root_item, "roomFriendSearch")
    wait_until(lambda: friends.property("count") == 1001)
    QTest.qWait(80)
    assert count_rows(root_item, "roomInvite-") < 30
    search.setProperty("text", "nGOC aNH")
    wait_until(lambda: friends.property("count") == 1)
    button = find_control(root_item, "roomInvite-online")
    assert find_item(root_item, "roomInvite-offline") is None
    press(view, button)
    wait_until(lambda: gateway.invited == ["online"])
    gateway.snapshot = replace(
        gateway.snapshot,
        friends=tuple(
            replace(f, online=False) if f.account_id == "online" else f
            for f in gateway.snapshot.friends
        ),
    )
    social.refresh()
    wait_until(lambda: not social.busy and friends.property("count") == 0)
    assert find_control(root_item, "roomFriendSearchEmpty").property("visible")
    press(view, find_control(root_item, "roomFriendSearchClear"))
    wait_until(lambda: friends.property("count") == 1000)
    assert count_rows(root_item, "roomInvite-") < 30
