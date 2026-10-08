"""Online Minecraft sign-in offers Google once, without granting service privileges."""

from threading import Event
from typing import Any

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import preview as preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import Account, Launcher
from nostalgia.errors import SocialError
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control, press
from social_fixture import SocialFixture

pytestmark = pytest.mark.usefixtures("qt_app")


def sign_in_online(
    preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, account_kind: str
) -> None:
    _launcher, _gateway, view, root_item, *_ = preview
    monkeypatch.setattr(AccountBridge, "_fetch_missing_skins", lambda _self: None)
    monkeypatch.setattr(AccountBridge, "_prefetch_skin_support", lambda _self: None)

    def authenticate(_self: Launcher, *_args: Any, **_kwargs: Any) -> Account:
        return _self._store(Account("JunOnline", "0" * 32, account_kind))

    method = "add_microsoft_account" if account_kind == "microsoft" else "add_ely_account"
    monkeypatch.setattr(Launcher, method, authenticate)
    if account_kind == "microsoft":
        view.rootContext().contextProperty("bridge").signInMicrosoft()
    else:
        view.rootContext().contextProperty("accountBridge").signInEly("jun", "fixture", "")
    wait_until(lambda: bool(find_control(root_item, "googleLinkStep").property("visible")))
    wait_for_background()


@pytest.mark.parametrize(
    "account_kind,provider_name", [("microsoft", "Microsoft"), ("ely", "Ely.by")]
)
def test_online_success_offers_link_and_skip_persists(
    social_preview: tuple[Any, ...],
    monkeypatch: pytest.MonkeyPatch,
    account_kind: str,
    provider_name: str,
) -> None:
    launcher, _gateway, view, root_item, social, *_ = social_preview
    sign_in_online(social_preview, monkeypatch, account_kind)
    onboarding = view.rootContext().contextProperty("googleLinkBridge")
    assert onboarding.provider == provider_name and root_item.property("loginVisible")
    assert not find_control(root_item, "minimalLogin").property("visible")
    assert view.rootContext().contextProperty("bridge").activePlayerName == "JunOnline"
    press(view, find_control(root_item, "googleLinkLater"))
    assert not onboarding.pending and not root_item.property("loginVisible")
    assert not social.signedIn and not social.account
    returning, returning_bridge = open_preview(launcher, social_gateway=SocialFixture())
    try:
        assert not returning.rootObject().property("loginVisible")
        if account_kind == "microsoft":
            returning_bridge.signInMicrosoft()
            wait_until(lambda: not returning_bridge.busy)
        else:
            accounts = returning.rootContext().contextProperty("accountBridge")
            accounts.signInEly("jun", "fixture", "")
            wait_until(lambda: not accounts.busy)
        assert not returning.rootContext().contextProperty("googleLinkBridge").pending
    finally:
        wait_for_background()
        returning.close()
        returning.deleteLater()


def test_link_waits_for_verified_snapshot_and_free_stays_free(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, _gateway, view, root_item, social, *_rest, urls = social_preview
    sign_in_online(social_preview, monkeypatch, "microsoft")
    press(view, find_control(root_item, "googleLinkConnect"))
    wait_until(lambda: social.signingIn and not social.busy)
    assert urls and urls[-1].startswith("https://accounts.google.com/")
    assert root_item.property("loginVisible") and not social.signedIn
    social._poll_login()
    wait_until(lambda: social.signedIn and not social.busy)
    assert not root_item.property("loginVisible")
    assert not social.account["plus"] and not social.account["cosmeticPlus"]
    assert view.rootContext().contextProperty("bridge").activePlayerName == "JunOnline"


def test_error_can_retry_and_defer_cancels_google_polling(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, gateway, view, root_item, social, *_ = social_preview
    sign_in_online(social_preview, monkeypatch, "ely")
    start_login = gateway.start_login

    def unavailable() -> None:
        raise SocialError("Không kết nối được Google")

    monkeypatch.setattr(gateway, "start_login", unavailable)
    press(view, find_control(root_item, "googleLinkConnect"))
    wait_until(lambda: bool(social.note) and not social.busy)
    assert root_item.property("loginVisible") and "Google" in social.note
    monkeypatch.setattr(gateway, "start_login", start_login)
    press(view, find_control(root_item, "googleLinkConnect"))
    wait_until(lambda: social.signingIn and not social.busy)
    press(view, find_control(root_item, "googleLinkLater"))
    assert not social.signingIn and not social._login_timer.isActive()
    assert not root_item.property("loginVisible") and not social.signedIn
    social._poll_login()
    QTest.qWait(40)
    assert not social.signedIn


def test_google_already_connected_skips_online_link_step(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, gateway, view, root_item, social, *_ = social_preview
    gateway.access_token = "a" * 64
    social.refresh()
    wait_until(lambda: social.signedIn and not social.busy)
    monkeypatch.setattr(AccountBridge, "_fetch_missing_skins", lambda _self: None)
    monkeypatch.setattr(
        Launcher,
        "add_microsoft_account",
        lambda *_a, **_k: launcher._store(Account("LinkedPlayer", "1" * 32, "microsoft")),
    )
    bridge = view.rootContext().contextProperty("bridge")
    bridge.signInMicrosoft()
    wait_until(lambda: bridge.activePlayerName == "LinkedPlayer" and not bridge.busy)
    assert not root_item.property("loginVisible")
    assert not view.rootContext().contextProperty("googleLinkBridge").pending


def test_missing_google_service_is_skippable(preview: tuple[Any, ...]) -> None:
    _launcher, view, bridge, root_item = preview
    bridge.signInFinished.emit("Preview")
    assert root_item.property("loginVisible")
    connect = find_control(root_item, "googleLinkConnect")
    assert not connect.property("clickable")
    assert "chưa khả dụng" in find_control(root_item, "googleLinkStatus").property("text")
    press(view, find_control(root_item, "googleLinkLater"))
    assert not view.rootContext().contextProperty("googleLinkBridge").pending


@pytest.mark.parametrize("scale", [100, 150])
def test_link_and_defer_remain_reachable_on_small_screen(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, scale: int
) -> None:
    _launcher, _gateway, view, root_item, social, *_ = social_preview
    sign_in_online(social_preview, monkeypatch, "microsoft")
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, True, True, "vi"
    )
    QTest.qWait(60)

    def check_actions() -> None:
        for name in ("googleLinkConnect", "googleLinkLater"):
            control = find_control(root_item, name)
            point = control.mapToScene(QPointF())
            assert point.x() >= 0 and point.x() + control.width() <= view.width()
            assert point.y() >= 0 and point.y() + control.height() <= view.height()

    check_actions()
    press(view, find_control(root_item, "googleLinkConnect"))
    wait_until(lambda: social.signingIn and not social.busy)
    check_actions()
    press(view, find_control(root_item, "googleLinkLater"))
    assert not root_item.property("loginVisible")


def test_defer_drops_late_google_start_response(
    social_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, gateway, view, root_item, social, *_ = social_preview
    sign_in_online(social_preview, monkeypatch, "microsoft")
    started, release = Event(), Event()
    start_login = gateway.start_login

    def slow_start() -> Any:
        started.set()
        assert release.wait(3)
        return start_login()

    monkeypatch.setattr(gateway, "start_login", slow_start)
    press(view, find_control(root_item, "googleLinkConnect"))
    try:
        wait_until(started.is_set)
        press(view, find_control(root_item, "googleLinkLater"))
    finally:
        release.set()
    wait_until(lambda: not social.busy)
    assert not root_item.property("loginVisible") and not social.signingIn
    assert not social.signedIn and not gateway.access_token
