"""Cài đặt phân biệt dịch vụ chưa vận hành với công tắc thật, không xin đồng ý trước."""

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_main_window import Preview
from test_main_window import preview as preview
from test_usage_consent import usage_ready as usage_ready

from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def not_ready(
    monkeypatch: pytest.MonkeyPatch, usage_ready: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    assert not usage_ready
    monkeypatch.setenv("NOSTALGIA_USAGE_READY", "0")
    return usage_ready


@pytest.fixture
def unavailable_view(not_ready: list[dict[str, Any]], preview: Preview) -> Preview:
    assert not not_ready
    return preview


@pytest.fixture
def available_view(usage_ready: list[dict[str, Any]], preview: Preview) -> Preview:
    assert not usage_ready
    return preview


def _settings_card(preview: Preview, language: str, scale: int) -> Any:
    _launcher, view, _bridge, root_item = preview
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, True, True, False, language
    )
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 6)
    QTest.qWait(100)
    card = find_control(root_item, "usageSettingsCard")
    scroll = card.parentItem()
    while scroll.property("contentY") is None:
        scroll = scroll.parentItem()
    top = card.mapToItem(scroll, QPointF(0, 0)).y() + scroll.property("contentY")
    scroll.scrollBy(top - scroll.property("contentY"), True)
    QTest.qWait(100)
    return card


@pytest.mark.parametrize("language", ["en", "vi"])
@pytest.mark.parametrize("scale", [100, 150])
def test_unavailable_status_replaces_dead_toggle_and_preserves_refusal(
    unavailable_view: Preview,
    usage_ready: list[dict[str, Any]],
    language: str,
    scale: int,
    tmp_path: Path,
) -> None:
    launcher, view, _bridge, root_item = unavailable_view
    usage = view.rootContext().contextProperty("usageBridge")
    usage.choose(False)
    card = _settings_card(unavailable_view, language, scale)
    assert not find_control(card, "usageStatisticsToggle").isVisible()
    assert find_control(card, "usageUnavailableStatus").property("text") == (
        "Not available yet" if language == "en" else "Chưa khả dụng"
    )
    purpose = find_control(card, "usagePurpose").property("text")
    assert ("prioritize testing" if language == "en" else "ưu tiên kiểm thử") in purpose
    usage.choose(True)
    assert launcher.load_settings().usage_choice_v1 == "declined"
    press(view, find_control(card, "viewUsagePayload"))
    dialog = find_control(root_item, "usagePayloadDialog")
    wait_until(lambda: dialog.property("opened"))
    assert not usage_ready and not (launcher.paths.config_dir / "usage-day.json").exists()
    dialog.close()
    capture = card.grabToImage()
    assert capture is not None
    wait_until(lambda: not capture.image().isNull())
    assert capture.saveToFile(str(tmp_path / f"unavailable-{language}-{scale}.png"))
    assert view.grabWindow().save(str(tmp_path / f"settings-{language}-{scale}.png"))


def test_ready_toggle_accepts_and_revokes_with_keyboard(
    available_view: Preview, usage_ready: list[dict[str, Any]]
) -> None:
    launcher, view, _bridge, _root_item = available_view
    usage = view.rootContext().contextProperty("usageBridge")
    usage.choose(False)
    card = _settings_card(available_view, "en", 100)
    toggle = find_control(card, "usageStatisticsToggle")
    assert toggle.isVisible() and toggle.isEnabled()
    assert not find_control(card, "usageUnavailableStatus").isVisible()
    press(view, toggle, Qt.Key.Key_Space)
    wait_until(lambda: len(usage_ready) == 1 and not usage.busy)
    assert toggle.property("checked")
    press(view, toggle, Qt.Key.Key_Space)
    assert not toggle.property("checked")
    assert launcher.load_settings().usage_choice_v1 == "declined"
    usage._tick()
    assert len(usage_ready) == 1 and not (launcher.paths.config_dir / "usage-day.json").exists()


@pytest.mark.parametrize("choice", ["unselected", "accepted"])
def test_unavailable_service_still_allows_explicit_refusal_and_withdrawal(
    unavailable_view: Preview, usage_ready: list[dict[str, Any]], choice: str
) -> None:
    launcher, view, _bridge, _root_item = unavailable_view
    if choice == "accepted":
        view.rootContext().contextProperty("settingsBridge").setUsageChoice("accepted")
    card = _settings_card(unavailable_view, "vi", 100)
    refusal = find_control(card, "usageSettingsDecline")
    assert refusal.isVisible() and refusal.isEnabled()
    press(view, refusal)
    assert launcher.load_settings().usage_choice_v1 == "declined"
    assert not refusal.isVisible()
    assert not usage_ready and not (launcher.paths.config_dir / "usage-day.json").exists()
