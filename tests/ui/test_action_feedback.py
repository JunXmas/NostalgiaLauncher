"""Lý do khóa phải hiện tại chỗ, cập nhật theo trạng thái và không gọi thao tác bị khóa."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_host_popup import host_popup as host_popup
from test_instance_library import prepare
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import Instance, RoomStatus
from nostalgia.multiplayer.peer_failure import connection_failure
from nostalgia.social.model import Friend
from nostalgia.ui.translations import load_translations, phrase
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("language,scale", [("vi", 100), ("en", 150)])
def test_host_explains_game_account_storage_and_login_requirements(
    host_popup: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, language: str, scale: int
) -> None:
    _launcher, view, bridge, root_item, host, warnings = host_popup
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, True, True, language
    )
    calls: list[str] = []
    monkeypatch.setattr(
        bridge, "play_hosted", lambda instance_id, *_args: calls.append(instance_id)
    )
    host.openSetup()
    popup = find_control(root_item, "hostDialog")
    wait_until(lambda: popup.property("opened"))
    button = find_control(root_item, "hostLaunchButton")
    hint = find_control(root_item, "hostLaunchHint")
    checks: tuple[tuple[Callable[[], None], Callable[[], None], str], ...] = (
        (
            lambda: bridge._set_busy(True),
            lambda: bridge._set_busy(False),
            "Launcher đang thực hiện thao tác khác. Hãy chờ hoàn tất.",
        ),
        (
            lambda: bridge.setStorageBusy(True),
            lambda: bridge.setStorageBusy(False),
            "Đang xử lý dữ liệu bản chơi. Hãy chờ hoàn tất.",
        ),
        (
            lambda: bridge._set_game_running(True),
            lambda: bridge._set_game_running(False),
            "Minecraft đang chạy. Đóng game trước khi mở bản chơi khác.",
        ),
    )
    for activate, release, source in checks:
        activate()
        assert not button.property("clickable") and hint.isVisible()
        assert hint.property("text") == phrase(source, language)
        assert button.property("disabledReason") == hint.property("text")
        QTest.qWait(30)
        origin = hint.mapToScene(QPointF())
        assert origin.y() >= 0 and origin.y() + hint.height() <= view.height()
        press(view, button)
        assert not calls
        release()
        assert button.property("clickable") and not hint.isVisible()
    bridge._accounts = ()
    bridge.activeAccountChanged.emit()
    assert "Minecraft" in hint.property("text") and not button.property("clickable")
    bridge.announce_accounts_changed()
    view.rootContext().contextProperty("socialBridge").signOut()
    wait_until(lambda: not button.property("clickable"))
    assert "Google" in hint.property("text")
    assert not warnings, "\n".join(warnings)


@pytest.mark.parametrize("language", ["vi", "en"])
def test_guest_sees_room_peer_and_world_separately_and_can_retry_in_place(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, language: str
) -> None:
    launcher, _gateway, view, root_item, _social, room, _sync, _urls = social_preview
    login_preview(social_preview)
    view.resize(1440, 900)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        100, False, True, True, language
    )
    launcher.save_instance(Instance("selected", "1.20.1", "World pack"))
    view.rootContext().contextProperty("bridge").announce_instances_changed()
    find_control(root_item, "friendsPage").setProperty("section", 1)
    status = RoomStatus(
        role="joined",
        local_port=25566,
        world_ready=False,
        connection_kind="pending",
        lobby_verified=True,
    )
    room._apply_status(status)
    QTest.qWait(40)
    button = find_control(root_item, "launchGuestRoom")
    hint = find_control(root_item, "guestLaunchHint")
    assert find_control(root_item, "roomStage-room").isVisible()
    assert not button.property("clickable")
    assert hint.property("text") == phrase(
        "Chờ host mở world và bật Open to LAN trong Minecraft.", language
    )
    room._apply_status(replace(status, world_available=True, connection_kind="connecting"))
    assert "World" in find_control(root_item, "roomStage-world").property("text")
    assert not button.property("clickable")
    room._apply_status(
        replace(status, world_available=True, world_ready=True, connection_kind="direct")
    )
    assert button.property("clickable") and not hint.isVisible()
    note = str(connection_failure("signalling"))
    room._apply_status(
        replace(
            status,
            world_available=True,
            connection_kind="failed",
            connection_note=note,
            connection_retryable=True,
        )
    )
    assert not button.property("clickable") and hint.isVisible()
    assert (
        find_control(root_item, "roomConnectionNote").property("text")
        == load_translations(language)["m:" + note]
    )
    retry_calls: list[bool] = []
    monkeypatch.setattr(room._service, "retry_connection", lambda: retry_calls.append(True))
    press(view, find_control(root_item, "retryRoomConnection"))
    assert retry_calls == [True]
    room._apply_status(replace(status, connection_kind="failed", connection_retryable=False))
    assert not find_control(root_item, "retryRoomConnection").isVisible()
    assert hint.property("text") == phrase(
        "Nhờ host gửi lời mời mới, rồi rời phòng này để vào lại.", language
    )


@pytest.mark.parametrize("content_kind", ["mod", "shader", "resourcepack"])
def test_global_install_explains_missing_target_then_installs_only_into_selected_instance(
    preview: Preview, monkeypatch: pytest.MonkeyPatch, content_kind: str
) -> None:
    _launcher, view, _bridge, root_item = preview
    calls = prepare(preview, monkeypatch)
    find_control(root_item, "modernInstanceManager").close()
    root_item.setProperty("currentIndex", 2)
    library = find_control(root_item, "minimalLibrary")
    library.setProperty("kind", content_kind)
    library.refresh()
    content = view.rootContext().contextProperty("contentBridge")
    wait_until(lambda: not content.searching and bool(content.results))
    project = view.rootContext().contextProperty("projectBridge")
    project.openProject("demo")
    popup = find_control(root_item, "projectDialog")
    wait_until(lambda: popup.property("opened") and not project.details["loading"])
    button = find_control(root_item, "projectInstall")
    hint = find_control(root_item, "projectInstallHint")
    assert not button.property("clickable") and hint.isVisible()
    assert "Cài vào bản chơi" in hint.property("text")
    QTest.qWait(80)
    position = button.mapToScene(QPointF(button.width() / 2, button.height() / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=position)
    assert not calls
    assert popup.property("opened"), "bấm nút cài đang khóa không được đóng popup"
    picker = find_control(root_item, "projectVersionPicker")
    picker.setProperty("instanceId", "other")
    wait_until(lambda: button.property("clickable") and not hint.isVisible())
    press(view, button)
    wait_until(lambda: bool(calls) and not project.installing)
    assert calls[0].instance_id == "other" and calls[0].content_kind == content_kind


def test_many_friend_requests_are_virtualized_and_last_request_remains_actionable(
    social_preview: tuple[Any, ...],
) -> None:
    _launcher, gateway, view, root_item, social, *_others = social_preview
    login_preview(social_preview)
    social._timer.stop()
    gateway.snapshot = replace(
        gateway.snapshot,
        requests=tuple(Friend(f"request-{n}", f"Player {n}", False, True) for n in range(1000)),
    )
    social.refresh()
    wait_until(lambda: not social.busy and len(social.requests) == 1000)
    requests = find_control(root_item, "friendRequestsList")
    assert requests.property("count") == 1000 and requests.height() <= 320
    delegates = requests.property("contentItem").childItems()
    assert len(delegates) < 30
    requests.positionViewAtEnd()
    QTest.qWait(80)
    scroll = find_control(root_item, "friendsScroll")
    scroll.setProperty("contentY", scroll.property("maxY"))
    QTest.qWait(80)
    button = find_control(requests, "acceptFriend-request-999")
    assert button.isVisible() and button.property("clickable")
    press(view, button)
    wait_until(lambda: gateway.accepted == ["request-999"])
