"""Cầu nối CHƠI CHUNG: trạng thái từ luồng dịch vụ tới QML đúng luồng; trang QML nạp được."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication
from PySide6.QtTest import QTest

from nostalgia.api import Launcher
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def wait_until(predicate, milliseconds: int = 4000) -> None:
    waited = 0
    while waited < milliseconds and not predicate():
        QCoreApplication.processEvents()
        QTest.qWait(20)
        waited += 20
    assert predicate(), "hết giờ chờ trạng thái tới luồng giao diện"


def test_status_crosses_threads_and_secret_stays_grouped(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    multiplayer_bridge = MultiplayerBridge(launcher)
    changes: list[int] = []
    multiplayer_bridge.statusChanged.connect(lambda: changes.append(1))
    try:
        assert (multiplayer_bridge.role, multiplayer_bridge.active) == ("idle", False)
        multiplayer_bridge.startHosting()
        wait_until(lambda: multiplayer_bridge.role == "waiting_world")
        assert len(multiplayer_bridge.roomCode) == 18
        assert multiplayer_bridge.roomCodeSpaced == " ".join(
            multiplayer_bridge.roomCode[i : i + 6] for i in (0, 6, 12)
        )
        multiplayer_bridge.stop()
        wait_until(lambda: multiplayer_bridge.role == "idle")
        assert multiplayer_bridge.roomCode == ""
    finally:
        multiplayer_bridge.shutdown()


def test_failure_signal_reaches_the_gui_thread(tmp_path: Path) -> None:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    multiplayer_bridge = MultiplayerBridge(launcher)
    failures: list[str] = []
    multiplayer_bridge.failed.connect(failures.append)
    try:
        multiplayer_bridge.join("ABC")
        wait_until(lambda: bool(failures))
        assert "mã phòng" in failures[0] and multiplayer_bridge.role == "idle"
        multiplayer_bridge._apply_status(RoomStatus(role="hosting", room_code="A" * 18))
        assert multiplayer_bridge.active and multiplayer_bridge.roomCodeSpaced.count(" ") == 2
    finally:
        multiplayer_bridge.shutdown()
