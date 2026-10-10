"""Polling nền không tải chat; thao tác trực tiếp và mở lại chat vẫn làm mới ngay."""

from typing import Any

import pytest
from test_bridges import wait_until
from test_minimal_preview import find_control
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import FriendMessage

pytestmark = pytest.mark.usefixtures("qt_app")


def test_idle_friend_page_does_not_enable_fast_snapshot_polling(
    social_preview: tuple[Any, ...],
) -> None:
    *_, social, _multiplayer, _sync, _urls = social_preview
    login_preview(social_preview)
    social.setWatching(True)
    assert social._timer.interval() == 15000
    social.selectFriend("misa")
    wait_until(lambda: social.peerId == "misa" and not social.busy)
    assert social._timer.interval() == 5000
    social.selectFriend("")
    assert social._timer.interval() == 15000


def test_background_refresh_preserves_chat_without_fetch_and_reopening_is_immediate(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, gateway, _view, root_item, social, *_ = social_preview
    login_preview(social_preview)
    calls: list[str] = []
    original = gateway.fetch_messages

    def fetch(account_id: str) -> Any:
        calls.append(account_id)
        return original(account_id)

    monkeypatch.setattr(gateway, "fetch_messages", fetch)
    social.selectFriend("misa")
    wait_until(lambda: social.messages and not social.busy)
    before = social.messages
    calls.clear()
    page = find_control(root_item, "friendsPage")
    page.setProperty("section", 1)
    assert social._timer.interval() == 15000
    social._timer.stop()
    gateway.messages.append(FriendMessage("new", "misa", "Tin mới", 2))
    social.refresh()
    wait_until(lambda: not social.busy)
    assert not calls and social.messages == before
    page.setProperty("section", 0)
    wait_until(lambda: calls == ["misa"] and not social.busy)
    assert social.messages[-1]["text"] == "Tin mới"
    assert social._timer.interval() == 5000
