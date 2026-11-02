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


def test_large_friend_list_search_normalizes_names_without_network(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, gateway, view, root_item, *_ = social_preview
    gateway.snapshot = replace(
        gateway.snapshot,
        invitations=(),
        friends=(
            *(Friend(str(i), f"Bạn {i:04d}") for i in range(1999)),
            Friend("selected", "Đặng Nhật Minh"),
        ),
    )
    login_preview(social_preview)
    calls: list[str] = []
    original = gateway.fetch_snapshot

    def snapshot() -> Any:
        calls.append("snapshot")
        return original()

    monkeypatch.setattr(gateway, "fetch_snapshot", snapshot)
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
    search.setProperty("text", "không tồn tại")
    wait_until(lambda: friends.property("count") == 0)
    assert find_control(root_item, "friendSearchEmpty").property("visible")
    press(view, find_control(root_item, "friendSearchClear"))
    wait_until(lambda: friends.property("count") == 2000)
    assert search.property("text") == "" and not calls
    assert count_rows(root_item, "friend-") < 40


def test_room_search_invites_every_matching_friend_and_follows_refresh(
    social_preview: tuple[Any, ...],
) -> None:
    _, gateway, view, root_item, social, multiplayer, *_ = social_preview
    gateway.snapshot = replace(
        gateway.snapshot,
        invitations=(),
        friends=(
            *(Friend(str(i), f"Bạn {i:04d}") for i in range(1000)),
            Friend("anh", "Ngọc Ánh"),
            Friend("removed", "Ngọc Ánh Hà"),
        ),
    )
    login_preview(social_preview)
    multiplayer._apply_status(
        RoomStatus(
            role="hosting",
            room_code="ABCDEFABCDEFGHJKMN",
            host_ticket="opaque-ticket",
            world_name="World",
        )
    )
    find_control(root_item, "friendsPage").setProperty("section", 1)
    friends = find_control(root_item, "roomFriends")
    search = find_control(root_item, "roomFriendSearch")
    wait_until(lambda: friends.property("count") == 1002)
    QTest.qWait(80)
    assert count_rows(root_item, "roomInvite-") < 30
    search.setProperty("text", "nGOC aNH")
    wait_until(lambda: friends.property("count") == 2)
    press(view, find_control(root_item, "roomInvite-anh"))
    wait_until(lambda: gateway.invited == ["anh"] and not social.inviteBusy)
    gateway.snapshot = replace(
        gateway.snapshot,
        friends=tuple(
            f for f in gateway.snapshot.friends if f.account_id not in ("anh", "removed")
        ),
    )
    social.refresh()
    wait_until(lambda: not social.busy and friends.property("count") == 0)
    assert find_control(root_item, "roomFriendSearchEmpty").property("visible")
    press(view, find_control(root_item, "roomFriendSearchClear"))
    wait_until(lambda: friends.property("count") == 1000)
    assert count_rows(root_item, "roomInvite-") < 30
