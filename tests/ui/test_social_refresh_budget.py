"""Bạn bè không poll: 5 phút giả lập chỉ tốn đúng số lần tải người dùng gây ra.

Mỗi `fetch_snapshot` là một `GET /v1/me` lên Worker free. Poll 15 s cũ tốn 20 lần mỗi 5 phút
cho mỗi máy đang mở launcher.
"""

from typing import Any

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.ui import social_session
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_five_idle_minutes_cost_only_focus_and_user_refreshes(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, gateway, view, root_item, social, *_ = social_preview
    clock = [1000.0]
    monkeypatch.setattr(social_session, "monotonic", lambda: clock[0])
    calls: list[float] = []
    original = gateway.fetch_snapshot

    def counted() -> Any:
        calls.append(clock[0])
        return original()

    monkeypatch.setattr(gateway, "fetch_snapshot", counted)
    login_preview(social_preview)
    assert calls == [1000.0]
    assert not [timer for timer in social.findChildren(QTimer) if timer.isActive()]

    # Cửa sổ được focus mỗi 5 s suốt 5 phút: chỉ tải lại khi đã quá 60 s từ lần trước.
    for _step in range(60):
        clock[0] += 5
        social.refreshStale()
        wait_until(lambda: not social.busy)
    assert calls == [1000.0, 1060.0, 1120.0, 1180.0, 1240.0, 1300.0]

    calls.clear()
    press(view, find_control(root_item, "refreshFriends"))
    wait_until(lambda: len(calls) == 1 and not social.busy)
    social.acceptFriend("minh")
    wait_until(lambda: len(calls) == 2 and not social.busy and not social.friendBusy)
    root_item.setProperty("currentIndex", 0)
    QTest.qWait(40)
    root_item.setProperty("currentIndex", 4)
    wait_until(lambda: len(calls) == 3 and not social.busy)
    QTest.qWait(200)
    assert len(calls) == 3
    assert not [timer for timer in social.findChildren(QTimer) if timer.isActive()]


def test_window_focus_reloads_friends_after_a_minute(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, gateway, view, _root_item, social, *_ = social_preview
    clock = [1000.0]
    monkeypatch.setattr(social_session, "monotonic", lambda: clock[0])
    login_preview(social_preview)
    calls: list[str] = []
    original = gateway.fetch_snapshot

    def counted() -> Any:
        calls.append("snapshot")
        return original()

    monkeypatch.setattr(gateway, "fetch_snapshot", counted)
    monkeypatch.setattr(type(view), "isActive", lambda _view: True)
    clock[0] += 30
    view.activeChanged.emit()
    QTest.qWait(40)
    assert not calls
    clock[0] += 31
    view.activeChanged.emit()
    wait_until(lambda: calls == ["snapshot"] and not social.busy)
