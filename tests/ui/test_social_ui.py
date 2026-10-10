"""Qt thật: Google trình duyệt, chat, lời mời và thu hồi phiên không khóa bản chơi."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF, QUrl, qInstallMessageHandler
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtTest import QSignalSpy, QTest
from test_bridges import wait_until
from test_minimal_preview import press

from nostalgia.api import Launcher, RoomStatus
from nostalgia.content.model import SearchPage
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background
from social_fixture import SocialFixture

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def social_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, ...]]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    launcher.add_offline_account("MinecraftName")
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    gateway = SocialFixture()
    urls = []

    def open_browser(url: QUrl) -> bool:
        urls.append(url.toString())
        return True

    monkeypatch.setattr(QDesktopServices, "openUrl", open_browser)
    view, bridge = open_preview(launcher, social_gateway=gateway)
    root_item = view.rootObject()
    assert root_item is not None
    view.show()
    view.requestActivate()
    root_item.setProperty("currentIndex", 4)
    social = view.rootContext().contextProperty("socialBridge")
    multiplayer = view.rootContext().contextProperty("multiplayerBridge")
    sync_bridge = view.rootContext().contextProperty("roomSyncBridge")
    QTest.qWait(40)
    yield launcher, gateway, view, root_item, social, multiplayer, sync_bridge, urls
    social.shutdown()
    multiplayer.shutdown()
    sync_bridge.cancel()
    bridge.cancelSignIn()
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def find_control(root_item: Any, name: str) -> Any:
    if root_item.objectName() == name:
        return root_item
    for child in root_item.childItems():
        found = find_control(child, name)
        if found is not None:
            return found
    return None


def login_preview(preview: tuple[Any, ...]) -> None:
    _, gateway, view, _, social, *_ = preview
    gateway.access_token = "a" * 64
    social.refresh()
    wait_until(lambda: social.signedIn and not social.busy)
    # Dữ liệu đã về chưa có nghĩa các vị trí sau đăng nhập đã được polish/render.
    frame = QSignalSpy(view.frameSwapped)
    view.update()
    assert frame.count() or frame.wait(2000), "khung đăng nhập chưa vẽ xong"


def test_google_opens_browser_and_account_is_separate_from_minecraft(
    social_preview: tuple[Any, ...],
) -> None:
    launcher, gateway, view, root_item, social, _, _, urls = social_preview
    press(view, find_control(root_item, "socialGoogleLogin"))
    wait_until(lambda: social.signingIn and not social.busy)
    assert urls and urls[0].startswith("https://accounts.google.com/")
    social._poll_login()
    wait_until(lambda: social.signedIn and not social.busy)
    assert gateway.access_token == "a" * 64
    assert social.account["name"] == "Jun PREVIEW" and not social.account["plus"]
    assert launcher.list_accounts()[0].player_name == "MinecraftName"
    assert not hasattr(social, "accessToken")


def test_free_chat_and_host_invite_do_not_need_plus(social_preview: tuple[Any, ...]) -> None:
    _, gateway, view, root_item, social, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    press(view, find_control(root_item, "friend-misa"))
    wait_until(lambda: social.peerId == "misa" and not social.busy)
    press(view, find_control(root_item, "showOptionalChat"))
    wait_until(lambda: social.messages and not social.busy)
    find_control(root_item, "chatComposer").setProperty("text", "Chơi thôi")
    press(view, find_control(root_item, "sendChat"))
    wait_until(lambda: gateway.sent and not social.busy)
    assert gateway.sent == ["Chơi thôi"]
    wait_until(lambda: len(social.messages) == 2 and not social.busy)
    assert not find_control(root_item, "inviteSelectedFriend").isVisible()
    assert find_control(root_item, "friendsOpenRoom").property("label") == "Tạo phòng"
    multiplayer._apply_status(
        RoomStatus(
            role="hosting",
            room_code="ABCDEFABCDEFGHJKMN",
            host_ticket="opaque-ticket",
            world_name="World",
        )
    )
    assert find_control(root_item, "inviteSelectedFriend").isVisible()
    assert find_control(root_item, "inviteSelectedFriend").property("label") == "Mời vào phòng"
    press(view, find_control(root_item, "inviteSelectedFriend"))
    wait_until(lambda: gateway.invited and not social.busy)
    assert gateway.invited == ["misa"]
    invite = find_control(root_item, "inviteSelectedFriend")
    status = multiplayer.room_snapshot()
    multiplayer._apply_status(replace(status, locked=True))
    assert not invite.isVisible()
    multiplayer._apply_status(status)
    sync_bridge.set_host_ready(False)
    assert not invite.isVisible()
    sync_bridge.set_host_ready(True)
    assert invite.isVisible()
    gateway.snapshot = replace(
        gateway.snapshot, friends=(replace(gateway.snapshot.friends[0], online=False),)
    )
    social.refresh()
    wait_until(lambda: not social.busy)
    assert not invite.isVisible()


def test_accept_invitation_joins_without_visible_room_code(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, view, root_item, _, _, sync_bridge, _ = social_preview
    login_preview(social_preview)
    codes: list[str] = []
    monkeypatch.setattr(sync_bridge, "join", codes.append)
    press(view, find_control(root_item, "acceptInvite-invite"))
    wait_until(lambda: bool(codes))
    assert codes == ["ABCDEFABCDEFGHJKMN"]
    assert root_item.findChild(type(root_item), "roomCodeInput") is None


def test_revoked_session_clears_social_and_stops_room(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, gateway, _, _, social, multiplayer, _, _ = social_preview
    login_preview(social_preview)
    stopped = []
    monkeypatch.setattr(multiplayer, "stop", lambda: stopped.append(True))
    gateway.revoked = True
    social.refresh()
    wait_until(lambda: not social.signedIn and not social.busy)
    assert not gateway.access_token and stopped
    assert "máy khác" in social.note
    assert launcher.list_accounts()


@pytest.mark.parametrize("scale", [100, 150])
def test_friends_panels_fit_small_and_desktop(social_preview: tuple[Any, ...], scale: int) -> None:
    _, _, view, root_item, social, _, _, _ = social_preview
    login_preview(social_preview)
    warnings = []
    qInstallMessageHandler(lambda _severity, _context, message: warnings.append(message))
    try:
        view.rootContext().contextProperty("settingsBridge").setAppearance(
            scale, False, False, True, "vi"
        )
        for width, height in [(1440, 900), (1024, 600)]:
            view.resize(width, height)
            QTest.qWait(60)
            page = find_control(root_item, "friendsPage")
            for name in ("friendsRail", "friendChat", "socialRoomPanel"):
                panel = find_control(root_item, name)
                if not panel.isVisible():
                    continue
                origin = panel.mapToItem(page, QPointF())
                assert origin.x() >= 0 and origin.x() + panel.width() <= page.width() + 0.5
        assert not warnings
        assert not social.account["plus"]
    finally:
        qInstallMessageHandler(None)
