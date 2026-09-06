"""Cầu nối CÀI ĐẶT: khoá CurseForge lưu xuống settings.json 0600, xoá được, không lộ ra QML."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from nostalgia.api import Launcher
from nostalgia.settings.store import settings_path
from nostalgia.ui.settings_bridge import SettingsBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_key_round_trip_through_the_bridge(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    settings_bridge = SettingsBridge(launcher)
    changes: list[int] = []
    settings_bridge.settingsChanged.connect(lambda: changes.append(1))

    assert settings_bridge.hasCurseforgeKey is False
    settings_bridge.saveCurseforgeKey("  $2a$10$abc  ")
    assert settings_bridge.hasCurseforgeKey is True
    assert stat.S_IMODE(settings_path(tmp_path / "config").stat().st_mode) == 0o600
    assert launcher.load_settings().curseforge_api_key == "$2a$10$abc"
    assert "curseforgeApiKey" not in [
        settings_bridge.metaObject().property(i).name()
        for i in range(settings_bridge.metaObject().propertyCount())
    ], "khoá thật không được lộ thành thuộc tính QML"

    settings_bridge.saveCurseforgeKey("")
    assert settings_bridge.hasCurseforgeKey is False
    assert len(changes) == 2
    assert settings_bridge.curseforgeKeyEnvName == "NOSTALGIA_CURSEFORGE_API_KEY"
