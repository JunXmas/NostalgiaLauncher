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


def test_valid_game_dir_root_saves_and_emits_changed(tmp_path: Path) -> None:
    """Đường dẫn hợp lệ → lưu xuống đĩa và phát gameDirRootChanged."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    settings_bridge = SettingsBridge(launcher)
    changed: list[str] = []
    errors: list[str] = []
    settings_bridge.gameDirRootChanged.connect(lambda: changed.append("changed"))
    settings_bridge.gameDirRootError.connect(errors.append)

    new_root = str(tmp_path / "o-D" / "Nostalgia")
    settings_bridge.setDefaultGameDirRoot(new_root)

    assert settings_bridge.defaultGameDirRoot == new_root
    assert launcher.load_settings().default_game_dir_root == new_root, "phải ghi xuống đĩa"
    assert changed == ["changed"]
    assert errors == [], "không có lỗi khi đường dẫn hợp lệ"


def test_invalid_game_dir_root_emits_error_not_saved(tmp_path: Path) -> None:
    """Đường dẫn không hợp lệ (tương đối, đè lên kho launcher) → gameDirRootError, không lưu.
    Đây là bug ban đầu: người chơi chọn ổ D gốc hoặc đường dẫn sai, cài đặt vẫn là ổ C
    mà không có thông báo gì — sau fix phải hiện lỗi rõ ràng."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    settings_bridge = SettingsBridge(launcher)
    changed: list[str] = []
    errors: list[str] = []
    settings_bridge.gameDirRootChanged.connect(lambda: changed.append("changed"))
    settings_bridge.gameDirRootError.connect(errors.append)

    # Đường dẫn tương đối — hợp lệ theo OS nhưng launcher từ chối
    settings_bridge.setDefaultGameDirRoot("relative/path")
    # Đường dẫn đè lên kho launcher
    settings_bridge.setDefaultGameDirRoot(str(tmp_path / "data"))

    assert settings_bridge.defaultGameDirRoot == "", "cài đặt không được thay đổi"
    assert launcher.load_settings().default_game_dir_root == "", "không ghi xuống đĩa"
    assert changed == [], "gameDirRootChanged không được phát"
    assert len(errors) == 2, "mỗi đường dẫn sai phát một lỗi"
