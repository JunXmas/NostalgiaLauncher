"""Real Qt interactions for the isolated design preview; no online credentials."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any, NoReturn

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QObject, QPoint, QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QWheelEvent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from test_bridges import wait_until

from nostalgia.api import Launcher
from nostalgia.auth.device_code import DeviceCode
from nostalgia.content.model import SearchPage
from nostalgia.errors import AuthError, TwoFactorRequired
from nostalgia.instance.model import Instance
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")

Preview = tuple[Launcher, QQuickView, LauncherBridge, Any]


@pytest.fixture
def preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Preview]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    view, bridge = open_preview(launcher)
    assert view.rootObject() is not None, [e.toString() for e in view.errors()]
    view.show()
    view.requestActivate()
    QTest.qWait(60)
    yield launcher, view, bridge, view.rootObject()
    bridge.cancelSignIn()
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def find_control(root_item: Any, name: str) -> Any:
    result = root_item.findChild(QObject, name)
    assert result is not None, name
    return result


def press(view: QQuickView, control: Any, key: Qt.Key = Qt.Key.Key_Return) -> None:
    control.forceActiveFocus()
    QTest.keyClick(view, key)
    QGuiApplication.processEvents()


def wheel(view: QQuickView, scroll: Any, angle: int = -120, pixels: int = 0) -> None:
    position = scroll.mapToScene(QPointF(scroll.width() / 2, scroll.height() / 2))
    event = QWheelEvent(
        position,
        position,
        QPoint(0, pixels),
        QPoint(0, angle),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    QGuiApplication.sendEvent(view, event)


def test_first_login_and_keyboard_offline_error_then_success(preview: Preview) -> None:
    launcher, view, bridge, root_item = preview
    assert root_item.property("loginVisible")
    press(view, find_control(root_item, "loginOffline"))
    field = find_control(root_item, "loginOfflineName")
    field.setProperty("text", "bad name!")
    press(view, find_control(root_item, "loginOfflineSubmit"))
    login = find_control(root_item, "minimalLogin")
    wait_until(lambda: bool(login.property("failure")) and not bridge.busy)
    assert root_item.property("loginVisible")
    assert not launcher.list_accounts()
    field.setProperty("text", "JunPreview")
    press(view, find_control(root_item, "loginOfflineSubmit"))
    wait_until(lambda: not root_item.property("loginVisible") and not bridge.busy)
    assert launcher.list_accounts()[0].player_name == "JunPreview"
    assert bridge.activePlayerName == "JunPreview"
    # A returning account enters the workspace on a fresh window.
    returning, _ = open_preview(launcher)
    assert not returning.rootObject().property("loginVisible")
    returning.close()
    returning.deleteLater()


def test_guest_exploration_does_not_create_an_account(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    press(view, find_control(root_item, "loginExplore"))
    assert root_item.property("currentIndex") == 2
    assert not root_item.property("loginVisible")
    assert not launcher.list_accounts()
    assert find_control(root_item, "minimalLibrary").property("visible")


def test_microsoft_device_code_cancel_reaches_worker(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, view, bridge, root_item = preview
    seen: list[CancelToken] = []

    def sign_in(
        _self: Launcher, *, on_device_code: Callable[[DeviceCode], None], cancel_token: CancelToken
    ) -> NoReturn:
        seen.append(cancel_token)
        on_device_code(DeviceCode("ABCD1234", "https://microsoft.com/link", "fake-secret"))
        deadline = time.monotonic() + 4
        while not cancel_token.is_cancelled() and time.monotonic() < deadline:
            time.sleep(0.01)
        cancel_token.raise_if_cancelled()
        raise AuthError("test timeout")

    monkeypatch.setattr(Launcher, "add_microsoft_account", sign_in)
    press(view, find_control(root_item, "loginMicrosoft"))
    dialog = find_control(root_item, "minimalDeviceLogin")
    wait_until(lambda: bool(dialog.property("visible")))
    assert dialog.property("code") == "ABCD1234"
    press(view, find_control(root_item, "cancelMicrosoft"))
    wait_until(lambda: not bridge.busy)
    assert seen[0].is_cancelled()
    assert not dialog.property("visible")
    assert root_item.property("loginVisible")


def test_ely_two_factor_keeps_password_for_retry_and_failure_clears_it(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, view, _bridge, root_item = preview
    credentials: list[tuple[str, str, str]] = []

    def sign_in(_self: Launcher, name: str, password: str, *, totp_code: str) -> NoReturn:
        credentials.append((name, password, totp_code))
        if not totp_code:
            raise TwoFactorRequired("2fa required")
        raise AuthError("Sai mã xác thực")

    monkeypatch.setattr(Launcher, "add_ely_account", sign_in)
    press(view, find_control(root_item, "loginEly"))
    find_control(root_item, "loginElyEmail").setProperty("text", " jun@example.com ")
    password = find_control(root_item, "loginElyPassword")
    password.setProperty("text", "example-password")
    press(view, find_control(root_item, "loginElySubmit"))
    login = find_control(root_item, "minimalLogin")
    worker = view.rootContext().contextProperty("accountBridge")
    wait_until(lambda: bool(login.property("needsTotp")) and not worker.busy)
    assert password.property("text") == "example-password"
    totp = login.findChild(QObject, "loginTotp")
    assert totp is not None
    totp.setProperty("text", "123456")
    press(view, find_control(root_item, "loginElySubmit"))
    wait_until(lambda: not worker.busy and not password.property("text"))
    assert credentials == [
        ("jun@example.com", "example-password", ""),
        ("jun@example.com", "example-password", "123456"),
    ]
    assert root_item.property("loginVisible")


def test_scroll_wheel_reversal_trackpad_reduce_motion_and_bounds(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    scroll = find_control(root_item, "homeScroll")
    root_item.setProperty("sessionSkipped", True)
    scroll.setProperty("contentHeight", 2400)
    wheel(view, scroll)
    assert scroll.property("settling")
    QTest.qWait(120)
    assert 0 < scroll.property("contentY") < 92
    # A second notch accumulates; reversal changes the destination without jumping.
    wheel(view, scroll)
    assert scroll.property("destination") == pytest.approx(184)
    wheel(view, scroll, angle=120)
    assert scroll.property("destination") == pytest.approx(92)
    wait_until(lambda: not scroll.property("settling"))
    assert scroll.property("contentY") == pytest.approx(92)
    # Pixel deltas already have OS inertia; no second smoothing layer.
    wheel(view, scroll, angle=0, pixels=-35)
    assert scroll.property("contentY") == pytest.approx(127)
    assert not scroll.property("settling")
    settings = view.rootContext().contextProperty("settingsBridge")
    settings.setAppearance(100, False, True, True, "vi")
    wheel(view, scroll)
    assert scroll.property("contentY") == pytest.approx(219)
    assert not scroll.property("settling")
    scroll.setProperty("contentHeight", 200)
    assert scroll.property("contentY") == 0
    assert scroll.property("destination") == 0


def test_resizing_all_preview_pages_and_live_instance_refresh(preview: Preview) -> None:
    launcher, view, bridge, root_item = preview
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        launcher.add_offline_account("JunPreview")
        bridge.announce_accounts_changed()
        home = find_control(root_item, "minimalHome")
        assert home.property("chosen") is None
        launcher.save_instance(Instance("survival", "1.21.1", display_name="Sinh tồn"))
        bridge.instancesChanged.emit()
        QTest.qWait(40)
        assert home.property("chosen")["instanceId"] == "survival"
        for scale in (100, 150):
            settings = view.rootContext().contextProperty("settingsBridge")
            settings.setAppearance(scale, False, False, True, "vi")
            view.resize(1024, 600)
            for page in range(7):
                root_item.setProperty("currentIndex", page)
                QTest.qWait(40)
        assert not warnings
    finally:
        qInstallMessageHandler(None)
