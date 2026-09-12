"""Nhật ký game thời gian thực: dòng từ luồng nền gom thành lô, tô cấp độ đúng, không phình
RAM, và trang NHẬT KÝ vẽ được chúng."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject
from test_bridges import wait_until
from test_qml import make_launcher

from nostalgia.ui.app import build_view
from nostalgia.ui.game_log import LEVEL_ROLE, MAX_LINES, GameLogFeed, classify_level

pytestmark = pytest.mark.usefixtures("qt_app")


def test_levels_follow_minecraft_log_format() -> None:
    assert classify_level("[12:00:01] [Render thread/INFO]: Backend library: LWJGL") == "info"
    assert classify_level("[12:00:02] [Worker-Main-3/WARN]: Missing sound for event") == "warn"
    assert (
        classify_level("[12:00:03] [Server thread/ERROR]: Encountered an unexpected exception")
        == "error"
    )
    assert classify_level("[12:00:03] [main/FATAL]: Failed to start") == "error"
    assert classify_level("java.lang.NullPointerException: Cannot invoke") == "error"
    assert classify_level("\tat net.minecraft.client.main.Main.main(Main.java:200)") == "error"
    assert classify_level("Caused by: java.io.IOException") == "error"
    assert classify_level("Setting user: Jun") == "info"


def test_lines_from_a_background_thread_land_in_the_model_in_batches() -> None:
    feed = GameLogFeed()
    feed.begin_session()

    def pump() -> None:
        for number in range(300):
            feed.receive(
                f"[00:00:00] [main/{'WARN' if number % 100 == 0 else 'INFO'}]: dòng {number}"
            )

    worker = threading.Thread(target=pump)
    worker.start()
    worker.join()
    assert feed.model.rowCount() == 0, "chưa tới nhịp gom thì model chưa đổi — không sự kiện/dòng"
    wait_until(lambda: feed.model.rowCount() == 300)
    feed.end_session()
    levels = [feed.model.data(feed.model.index(row, 0), LEVEL_ROLE) for row in (0, 1, 100)]
    assert levels == ["warn", "info", "warn"]
    assert feed.allText().splitlines()[299].endswith("dòng 299")
    assert list(feed.tail)[-1].endswith("dòng 299") and len(feed.tail) == 60


def test_the_log_never_grows_past_the_cap() -> None:
    feed = GameLogFeed()
    feed.reset()
    feed.begin_session()
    for number in range(MAX_LINES + 250):
        feed.receive(f"dòng {number}")
    feed.end_session()
    assert feed.model.rowCount() == MAX_LINES
    assert feed.model.lines[0] == "dòng 250", "bỏ dòng CŨ nhất, giữ dòng mới"

    feed.reset()
    feed.receive("dòng đầu của lần chạy mới, tới trước khi giao diện kịp mở phiên")
    feed.begin_session()
    assert feed.model.rowCount() == 0, "game chạy lần mới thì nhật ký cũ được xoá"
    feed.end_session()
    assert feed.model.lines == ["dòng đầu của lần chạy mới, tới trước khi giao diện kịp mở phiên"]


def test_log_page_renders_lines_with_levels(tmp_path: Path) -> None:
    view, bridge = build_view(make_launcher(tmp_path))
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 5)
    wait_until(lambda: root_item.findChild(QObject, "logList") is not None)
    feed = bridge.gameLog
    feed.begin_session()
    feed.receive("[12:00:01] [Render thread/INFO]: Backend library: LWJGL version 3.3.3")
    feed.receive("[12:00:02] [Render thread/WARN]: Shader missing")
    feed.receive("[12:00:03] [Server thread/ERROR]: Boom")
    feed.end_session()
    log_list = root_item.findChild(QObject, "logList")
    copy_button = root_item.findChild(QObject, "copyLogButton")
    assert log_list is not None and copy_button is not None
    # Binding của QML cập nhật ở nhịp sự kiện kế; chờ có hạn thay vì tin một lần processEvents.
    wait_until(lambda: log_list.property("count") == 3)
    wait_until(lambda: copy_button.property("clickable") is True)
    assert feed.allText().count("\n") == 2


def test_tail_snapshot_is_thread_safe() -> None:
    """Mô phỏng race condition: luồng nền ghi liên tục trong khi luồng chính đọc snapshot."""
    feed = GameLogFeed()
    stop = threading.Event()
    errors: list[str] = []

    def writer() -> None:
        n = 0
        while not stop.is_set():
            feed.receive(f"dòng {n}")
            n += 1

    worker = threading.Thread(target=writer)
    worker.start()
    try:
        for _ in range(200):
            try:
                snapshot = feed.tail_snapshot
                # Iterate the snapshot to ensure it's a stable copy
                _ = [line for line in snapshot]  # noqa: C416
            except RuntimeError as exc:
                errors.append(str(exc))
    finally:
        stop.set()
        worker.join()
    assert not errors, f"race condition detected: {errors}"

