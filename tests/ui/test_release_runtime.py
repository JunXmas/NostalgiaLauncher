"""Điểm vào release thật: dịch vụ chưa cấu hình không dùng demo và QML nạp đủ trang."""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QObject, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest

from nostalgia.api import Launcher
from nostalgia.ui.runtime import build_release_view
from nostalgia.ui.worker import wait_for_background


@pytest.mark.usefixtures("qt_app")
def test_release_pages_offline_and_invalid_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NOSTALGIA_ACCOUNT_URL", "")
    monkeypatch.setenv("NOSTALGIA_ROOM_SYNC_URL", "")
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    launcher.paths.config_dir.mkdir(exist_ok=True)
    (launcher.paths.config_dir / "services.json").write_text("{broken", encoding="utf-8")
    warnings: list[str] = []
    qInstallMessageHandler(lambda _severity, _context, message: warnings.append(message))
    view = build_release_view(launcher)
    try:
        assert view.errors() == []
        view.show()
        root_item = view.rootObject()
        assert root_item is not None
        root_item.setProperty("sessionSkipped", True)
        for page in range(7):
            root_item.setProperty("currentIndex", page)
            QTest.qWait(50)
        assert root_item.findChild(QObject, "serviceAccountUrl") is None
        assert root_item.findChild(QObject, "saveServiceSettings") is None
        assert root_item.findChild(QObject, "serviceStatus") is not None
        assert view.rootContext().contextProperty("plusFeaturesEnabled") is False
        assert view.rootContext().contextProperty("paymentBridge").details["stage"] == "unavailable"
        configuration = view.rootContext().contextProperty("serviceConfiguration")
        configuration.save("http://bad", "")
        assert "HTTPS" in configuration.note
        configuration.save("https://accounts.example.invalid", "https://relay.example.invalid")
        monkeypatch.setenv("NOSTALGIA_ACCOUNT_URL", "https://accounts.example.invalid")
        assert (
            launcher.load_service_configuration().account_url == "https://accounts.example.invalid"
        )
        assert not warnings
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(None)
