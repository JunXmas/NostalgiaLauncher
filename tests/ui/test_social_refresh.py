"""Đọc lại tài khoản trong lúc bận phải được thực hiện ngay khi worker xong."""

from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication
from test_bridges import wait_until

from nostalgia.api import Launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.social_bridge import SocialBridge
from nostalgia.ui.worker import wait_for_background
from social_fixture import SocialFixture

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("stop_session", [False, True])
def test_busy_account_refresh_is_deferred_and_cancelled_on_shutdown(
    tmp_path: Path, stop_session: bool
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    main = LauncherBridge(launcher)
    multiplayer = MultiplayerBridge(launcher)
    sync_bridge = RoomSyncBridge(launcher, main, multiplayer, None)
    gateway = SocialFixture()
    social = SocialBridge(gateway, multiplayer, sync_bridge)
    gateway.access_token = "a" * 64
    try:
        social._set_busy(True)
        social.refresh()
        social.refresh()
        assert not social.signedIn
        if stop_session:
            social.shutdown()
        social._set_busy(False)
        if stop_session:
            QGuiApplication.processEvents()
            assert not social.signedIn and not social.busy and not gateway.access_token
        else:
            wait_until(lambda: bool(social.signedIn) and not social.busy, seconds=2)
            assert social.property("account")["name"] == "Jun PREVIEW"
    finally:
        social.shutdown()
        multiplayer.shutdown()
        sync_bridge.cancel()
        wait_for_background()
