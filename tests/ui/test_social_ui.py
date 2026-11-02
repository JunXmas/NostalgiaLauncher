"""Qt thật: Google trình duyệt, lời mời và thu hồi phiên không khóa bản chơi."""

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
from test_main_window import press

from nostalgia.api import Launcher, RoomStatus
from nostalgia.content.model import SearchPage
from nostalgia.ui.window import open_window
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
    view, bridge = open_window(launcher, social_gateway=gateway)
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


def test_host_invite_does_not_need_plus(social_preview: tuple[Any, ...]) -> None:
    _, gateway, view, root_item, social, multiplayer, sync_bridge, _ = social_preview
    login_preview(social_preview)
    assert find_control(root_item, "friendsOpenRoom").property("label") == "Tạo phòng"
    multiplayer._apply_status(
        RoomStatus(
            role="hosting",
            room_code="ABCDEFABCDEFGHJKMN",
            host_ticket="opaque-ticket",
            world_name="World",
        )
    )
    find_control(root_item, "friendsPage").setProperty("section", 1)
    QTest.qWait(80)
    invite = find_control(root_item, "roomInvite-misa")
    assert invite.isVisible() and invite.property("label") == "Mời vào phòng"
    press(view, invite)
    wait_until(lambda: gateway.invited and not social.inviteBusy)
    assert gateway.invited == ["misa"] and not social.account["plus"]
    status = multiplayer.room_snapshot()
    multiplayer._apply_status(replace(status, locked=True))
    assert not invite.isVisible()
    multiplayer._apply_status(status)
    sync_bridge.set_host_ready(False)
    assert not invite.isVisible()
    sync_bridge.set_host_ready(True)
    assert invite.isVisible()


def test_accept_invitation_joins_without_visible_room_code(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, view, root_item, _, _, sync_bridge, _ = social_preview
    login_preview(social_preview)
    codes: list[str] = []
    monkeypatch.setattr(sync_bridge, "join", lambda code, _owner="": codes.append(code))
    press(view, find_control(root_item, "acceptInvite-invite"))
    wait_until(lambda: bool(codes))
    assert codes == ["ABCDEFABCDEFGHJKMN"]
    # Mã trong lời mời không hiện ra và không điền sẵn vào ô nhập mã.
    assert not find_control(root_item, "hostRoomCode").isVisible()
    assert find_control(root_item, "roomCodeInput").property("code") == ""


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
            for name in ("friendsRail", "roomCodeCard", "socialRoomPanel"):
                panel = find_control(root_item, name)
                if not panel.isVisible():
                    continue
                origin = panel.mapToItem(page, QPointF())
                assert origin.x() >= 0 and origin.x() + panel.width() <= page.width() + 0.5
        assert not warnings
        assert not social.account["plus"]
    finally:
        qInstallMessageHandler(None)
