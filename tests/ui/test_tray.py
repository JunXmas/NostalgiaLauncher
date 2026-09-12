"""Khay hệ thống (tray mode): thu gọn vào khay khi game chạy để giải phóng RAM."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtQuick import QQuickView

from nostalgia.api import Launcher
from nostalgia.ui.app import build_tray
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.settings_bridge import SettingsBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_tray_initialization_and_menu(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view = QQuickView()
    bridge = LauncherBridge(launcher, parent=view)
    settings_bridge = SettingsBridge(launcher, parent=view)

    tray = build_tray(view, bridge, settings_bridge)
    assert tray.toolTip() == "Nostalgia Launcher"

    menu = tray.contextMenu()
    assert menu is not None
    actions = menu.actions()
    action_texts = [action.text() for action in actions if not action.isSeparator()]
    assert action_texts == ["Hiện lại Launcher", "Dừng game", "Thoát"]


def test_tray_hides_window_when_game_starts_and_restores_on_stop(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view = QQuickView()
    view.show()
    assert view.isVisible() is True

    bridge = LauncherBridge(launcher, parent=view)
    settings_bridge = SettingsBridge(launcher, parent=view)
    assert settings_bridge.hideWhenGameRunning is True

    tray = build_tray(view, bridge, settings_bridge)
    assert tray.isVisible() is False

    # Khi game khởi động, launcher ẩn và khay hiện
    bridge.gameStarted.emit("instance-1")
    assert view.isVisible() is False
    assert tray.isVisible() is True

    # Khi game dừng, khay ẩn và launcher hiện lại
    bridge.gameStopped.emit(0)
    assert tray.isVisible() is False
    assert view.isVisible() is True


def test_tray_does_not_hide_window_when_setting_is_disabled(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view = QQuickView()
    view.show()

    bridge = LauncherBridge(launcher, parent=view)
    settings_bridge = SettingsBridge(launcher, parent=view)
    settings_bridge.setHideWhenGameRunning(False)

    tray = build_tray(view, bridge, settings_bridge)
    bridge.gameStarted.emit("instance-1")
    assert view.isVisible() is True
    assert tray.isVisible() is False


def test_tray_menu_actions(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view = QQuickView()
    bridge = LauncherBridge(launcher, parent=view)
    settings_bridge = SettingsBridge(launcher, parent=view)

    tray = build_tray(view, bridge, settings_bridge)
    menu = tray.contextMenu()
    assert menu is not None
    actions = [a for a in menu.actions() if not a.isSeparator()]

    # Hành động Hiện lại Launcher
    view.hide()
    assert view.isVisible() is False
    actions[0].trigger()
    assert view.isVisible() is True

    # Hành động Dừng game
    stopped_calls: list[bool] = []
    bridge.stopGame = lambda: stopped_calls.append(True)  # type: ignore[method-assign]
    actions[1].trigger()
    assert stopped_calls == [True]
