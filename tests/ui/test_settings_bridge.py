"""Cầu nối CÀI ĐẶT: chỉ lộ phiên bản và thư mục dữ liệu, KHÔNG còn thuộc tính nào về khoá API."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from nostalgia import __version__
from nostalgia.api import Launcher
from nostalgia.ui.settings_bridge import SettingsBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_ui_sound_switch_persists(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    settings_bridge = SettingsBridge(launcher)
    assert settings_bridge.uiSound is True
    settings_bridge.setUiSound(False)
    assert settings_bridge.uiSound is False
    assert launcher.load_settings().ui_sound is False, "phải ghi xuống đĩa"


def test_hide_when_game_running_switch_persists(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    settings_bridge = SettingsBridge(launcher)
    assert settings_bridge.hideWhenGameRunning is True
    settings_bridge.setHideWhenGameRunning(False)
    assert settings_bridge.hideWhenGameRunning is False
    assert launcher.load_settings().hide_when_game_running is False, "phải ghi xuống đĩa"


def test_bridge_exposes_version_and_data_dir_only(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    settings_bridge = SettingsBridge(launcher)

    assert settings_bridge.launcherVersion == __version__
    assert settings_bridge.dataDir == str(tmp_path / "data")
    meta_object = settings_bridge.metaObject()
    exposed = {meta_object.property(i).name() for i in range(meta_object.propertyCount())}
    assert not {name for name in exposed if "urseforge" in name or "Key" in name}
