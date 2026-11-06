"""Nâng cấp cấu hình trước đợt xác nhận: hỏi lại đồng ý cũ, giữ nguyên từ chối."""

import json
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_usage_consent import usage_ready as usage_ready

from nostalgia.api import Launcher
from nostalgia.content.model import SearchPage
from nostalgia.ui.window import open_window
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("old_choice", ["accepted", "declined"])
@pytest.mark.parametrize(("language", "scale"), [("en", 100), ("vi", 150)])
def test_old_choice_and_finished_update_failure_do_not_lose_the_invitation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    usage_ready: list[dict[str, Any]],
    old_choice: str,
    language: str,
    scale: int,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.add_offline_account("UpgradeQA")
    launcher.paths.config_dir.mkdir(parents=True, exist_ok=True)
    settings_path = launcher.paths.config_dir / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "usage_choice_v1": old_choice,
                "auto_update_check": False,
                "discord_presence": False,
                "notification_sound": False,
                "ui_sound": False,
                "language": language,
                "ui_scale": scale,
            }
        )
    )
    day_path = launcher.paths.config_dir / "usage-day.json"
    day_path.write_text(json.dumps({"day": "2026-11-06", "daily_id": "f" * 32}))
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    view, bridge = open_window(launcher)
    view.resize(1024, 600)
    view.show()
    view.requestActivate()
    try:
        assert not view.rootObject().property("loginVisible")
        update_bridge = view.rootContext().contextProperty("updateBridge")
        update_bridge._set_state("failed", "The previous update check has finished")
        prompt = find_control(view.rootObject(), "usageConsentDialog")
        assert not day_path.exists() and not usage_ready
        if old_choice == "declined":
            QTest.qWait(1800)
            assert not prompt.property("opened")
            assert launcher.load_settings().usage_choice_v1 == "declined"
            return
        assert launcher.load_settings().usage_choice_v1 == "unselected"
        wait_until(lambda: prompt.property("opened"), seconds=4)
        assert view.grabWindow().save(str(tmp_path / f"upgrade-consent-{language}-{scale}.png"))
        assert not usage_ready
        usage = view.rootContext().contextProperty("usageBridge")
        usage.choose(True)
        wait_until(lambda: len(usage_ready) == 1)
        assert launcher.load_settings().usage_choice_v1 == "accepted"
        assert json.loads(settings_path.read_text())["usage_consent_revision"] == 1
        assert not prompt.property("opened")
    finally:
        bridge.cancelSignIn()
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
    returning, returning_bridge = open_window(launcher)
    returning.show()
    returning.requestActivate()
    try:
        QTest.qWait(1800)
        assert not find_control(returning.rootObject(), "usageConsentDialog").property("opened")
        assert len(usage_ready) == 1
    finally:
        returning_bridge.cancelSignIn()
        wait_for_background()
        returning.close()
        returning.deleteLater()
        QGuiApplication.processEvents()
