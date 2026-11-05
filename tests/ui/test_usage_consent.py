"""Hộp thoại một lần và cài đặt đi qua cầu nối thật; bắt request tại transport."""

import json
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_main_window import Preview
from test_main_window import preview as preview

from nostalgia.net.http import HttpClient, HttpResponse
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def usage_ready(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    monkeypatch.setenv("NOSTALGIA_USAGE_ENDPOINT", "https://usage.test/v1/usage")
    monkeypatch.setenv("NOSTALGIA_USAGE_READY", "1")

    def capture(_self: HttpClient, _method: str, url: str, **options: Any) -> HttpResponse:
        assert url == "https://usage.test/v1/usage"
        options["cancel_token"].raise_if_cancelled()
        requests.append(json.loads(options["body"]))
        return HttpResponse(200, b"{}", ())

    monkeypatch.setattr(HttpClient, "send", capture)
    return requests


@pytest.fixture
def usage_view(usage_ready: list[dict[str, Any]], preview: Preview) -> Preview:
    assert not usage_ready
    return preview


def test_prompt_defers_login_busy_and_existing_modal(usage_view: Preview) -> None:
    _launcher, _view, bridge, root_item = usage_view
    prompt = find_control(root_item, "usageConsentDialog")
    QTest.qWait(1700)
    assert not prompt.property("opened")
    root_item.setProperty("sessionSkipped", True)
    bridge._set_busy(True)
    QTest.qWait(1700)
    assert not prompt.property("opened")
    bridge._set_busy(False)
    confirm = find_control(root_item, "confirmDialog")
    confirm.ask("Other task", "Waiting", None)
    QTest.qWait(1700)
    assert not prompt.property("opened")
    confirm.dismiss()
    wait_until(lambda: prompt.property("opened"), seconds=4)


@pytest.mark.parametrize("action", ["decline", "escape", "close"])
def test_decline_escape_and_close_persist_and_do_not_ask_again(
    usage_view: Preview, usage_ready: list[dict[str, Any]], action: str
) -> None:
    launcher, view, _bridge, root_item = usage_view
    root_item.setProperty("sessionSkipped", True)
    prompt = find_control(root_item, "usageConsentDialog")
    wait_until(lambda: prompt.property("opened"), seconds=4)
    accept = find_control(root_item, "usageAccept")
    decline = find_control(root_item, "usageDecline")
    assert not accept.property("primary") and not decline.property("primary")
    assert accept.width() == decline.width()
    if action == "decline":
        press(view, decline)
    elif action == "escape":
        QTest.keyClick(view, Qt.Key.Key_Escape)
    else:
        close = next(
            child
            for child in prompt.property("contentItem").childItems()
            if child.property("label") == "\u00d7"
        )
        press(view, close)
    wait_until(lambda: launcher.load_settings().usage_choice_v1 == "declined")
    view.rootContext().contextProperty("settingsBridge").setAppearance(125, True, True, False, "en")
    assert launcher.load_settings().usage_choice_v1 == "declined"
    QTest.qWait(1700)
    assert not prompt.property("opened") and not usage_ready


def test_payload_view_is_local_and_settings_choice_suppresses_prompt(
    usage_view: Preview, usage_ready: list[dict[str, Any]]
) -> None:
    launcher, view, _bridge, root_item = usage_view
    usage = view.rootContext().contextProperty("usageBridge")
    usage.showPayload()
    dialog = find_control(root_item, "usagePayloadDialog")
    wait_until(lambda: dialog.property("opened"))
    assert not usage_ready and not (launcher.paths.config_dir / "usage-day.json").exists()
    dialog.close()
    usage.choose(False)
    root_item.setProperty("sessionSkipped", True)
    QTest.qWait(1700)
    assert not find_control(root_item, "usageConsentDialog").property("opened")


def test_accept_disable_and_game_signal_do_not_create_extra_events(
    usage_view: Preview, usage_ready: list[dict[str, Any]]
) -> None:
    launcher, view, bridge, root_item = usage_view
    root_item.setProperty("sessionSkipped", True)
    prompt = find_control(root_item, "usageConsentDialog")
    wait_until(lambda: prompt.property("opened"), seconds=4)
    press(view, find_control(root_item, "usageAccept"))
    usage = view.rootContext().contextProperty("usageBridge")
    wait_until(lambda: len(usage_ready) == 1 and not usage.busy)
    bridge.gameStarted.emit("private-world-not-for-statistics")
    QTest.qWait(100)
    assert len(usage_ready) == 1 and usage_ready[0]["event"] == "installation_active"
    usage.choose(False)
    usage._tick()
    assert len(usage_ready) == 1
    assert launcher.load_settings().usage_choice_v1 == "declined"
    assert not (launcher.paths.config_dir / "usage-day.json").exists()


def test_unavailable_service_never_prompts_or_creates_requests(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    usage = view.rootContext().contextProperty("usageBridge")
    assert not usage.available
    root_item.setProperty("sessionSkipped", True)
    QTest.qWait(1700)
    assert not find_control(root_item, "usageConsentDialog").property("opened")
    assert not (launcher.paths.config_dir / "usage-day.json").exists()


@pytest.mark.parametrize("language", ["en", "vi"])
@pytest.mark.parametrize("scale", [100, 150])
def test_small_window_large_text_and_payload_keyboard_navigation(
    usage_view: Preview,
    usage_ready: list[dict[str, Any]],
    language: str,
    scale: int,
    tmp_path: Path,
) -> None:
    launcher, view, _bridge, root_item = usage_view
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, True, True, False, language
    )
    root_item.setProperty("sessionSkipped", True)
    prompt = find_control(root_item, "usageConsentDialog")
    wait_until(lambda: prompt.property("opened"), seconds=4)
    assert prompt.property("width") <= view.width() - 40
    assert prompt.property("height") <= view.height() - 40
    body = find_control(root_item, "usageConsentBody")
    assert body.height() > 60
    assert prompt.property("title") == (
        "Help improve Nostalgia" if language == "en" else "Giúp cải thiện Nostalgia"
    )
    assert view.grabWindow().save(str(tmp_path / f"consent-{language}-{scale}.png"))
    press(view, find_control(root_item, "consentViewPayload"))
    payload_dialog = find_control(root_item, "usagePayloadDialog")
    wait_until(lambda: payload_dialog.property("opened"))
    assert find_control(root_item, "usagePayloadBody").height() > 80
    assert view.grabWindow().save(str(tmp_path / f"payload-{language}-{scale}.png"))
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: not payload_dialog.property("visible"))
    assert launcher.load_settings().usage_choice_v1 == "unselected" and not usage_ready
    QTest.keyClick(view, Qt.Key.Key_Escape)
    wait_until(lambda: launcher.load_settings().usage_choice_v1 == "declined")
