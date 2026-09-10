"""Nút DỪNG: game đang chạy thì nút CHƠI thành DỪNG (đỏ); bấm là tiến trình game bị dừng, cờ
gameRunning tắt, và vì là người dùng chủ động dừng nên không báo "gặp sự cố"."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject
from test_bridges import wait_until
from test_qml import make_launcher as make_offline_launcher

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.api import Instance
from nostalgia.ui.app import build_view
from nostalgia.ui.bridge import LauncherBridge
from test_api import make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")

# Java giả ngồi im 30 giây: chỉ có DỪNG mới làm nó thoát trước khi test hết hạn.
SLEEPING_JAVA = b"#!/bin/sh\nsleep 30\n"


def test_stop_kills_the_running_game_without_reporting_a_crash(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_launcher(
        server, server_state, tmp_path, certificate_pair, java_body=SLEEPING_JAVA
    )
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="thu", version_id=VERSION_ID))
    launcher.add_offline_account("Jun")
    bridge = LauncherBridge(launcher)
    stopped: list[int] = []
    failures: list[str] = []
    bridge.gameStopped.connect(stopped.append)
    bridge.failed.connect(failures.append)

    bridge.play("thu")
    wait_until(lambda: bridge.gameRunning is True)

    bridge.stopGame()
    wait_until(lambda: stopped != [] and not bridge.busy, seconds=15.0)

    assert bridge.gameRunning is False
    assert stopped == [0], "dừng chủ động = thoát bình thường, không phải mã tín hiệu"
    assert failures == [], "không toast 'gặp sự cố' khi chính người dùng bấm DỪNG"
    assert bridge.stopGame() is None, "không còn game: DỪNG là vô hại"


def test_play_button_turns_into_a_red_stop_button_while_the_game_runs(tmp_path: Path) -> None:
    launcher = make_offline_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="van", version_id="1.20.1"))
    launcher.add_offline_account("Jun")
    view, bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    button = root_item.findChild(QObject, "playButton")
    assert button is not None
    assert button.property("label") == "CHƠI  ▶" and button.property("danger") is False

    bridge._set_game_running(True)
    wait_until(lambda: button.property("label") == "DỪNG  ■")
    assert button.property("danger") is True and button.property("clickable") is True

    bridge._set_game_running(False)
    wait_until(lambda: button.property("label") == "CHƠI  ▶")
    assert button.property("danger") is False
