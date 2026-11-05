"""Cài mới mở giao diện tiếng Anh; lựa chọn tiếng Việt đã lưu vẫn được giữ."""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

from nostalgia.api import Launcher
from nostalgia.content.model import SearchPage
from nostalgia.ui.window import open_window
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("language", [None, "vi"])
def test_fresh_english_and_explicit_vietnamese_render(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, language: str | None
) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    settings = launcher.load_settings()
    assert settings.language == "en"
    launcher.save_settings(
        replace(
            settings,
            language=language or settings.language,
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    monkeypatch.setattr(Launcher, "load_promotions", lambda _self: ())
    view, _bridge = open_window(launcher)
    try:
        view.show()
        QTest.qWait(100)
        root_item = view.rootObject()
        assert root_item is not None, [error.toString() for error in view.errors()]
        assert find_control(root_item, "loginOffline").property("label") == (
            "Chơi ngoại tuyến" if language == "vi" else "Play offline"
        )
        assert launcher.load_settings().language == (language or "en")
        assert view.grabWindow().save(str(tmp_path / f"default-{language or 'en'}.png"))
    finally:
        view.rootContext().contextProperty("usageBridge").shutdown()
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
