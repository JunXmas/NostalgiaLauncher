"""Theo log của đúng bản chơi, gộp stdout và log, dừng theo dõi khi game đóng."""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject
from shiboken6 import delete
from test_bridges import wait_until

from nostalgia.ui.game_lan import GameLanFeed

pytestmark = pytest.mark.usefixtures("qt_app")


def test_selected_game_log_supplies_lan_and_does_not_repeat_stdout(tmp_path: Path) -> None:
    parent = QObject()
    feed = GameLanFeed(parent)
    received: list[tuple[str, int]] = []
    feed.lanOpened.connect(lambda instance_id, port: received.append((instance_id, port)))
    path = tmp_path / "latest.log"
    path.write_text("Started serving on 51234\n")
    stdout = feed.receiver("chosen", lambda _line: None, path)
    feed.begin_session()
    try:
        with path.open("a") as stream:
            stream.write("[Server thread/INFO]: Started serving on 54321\n")
        wait_until(lambda: received == [("chosen", 54321)])
        stdout("[Server thread/INFO]: Started serving on 54321")
        assert received == [("chosen", 54321)]
        generation = feed._generation
        feed.clear()
        feed._apply_port("chosen", 51234, generation)
        assert received == [("chosen", 54321)] and feed.port == 0
        assert feed._log_stop.is_set() and feed._log_follow is None
    finally:
        feed.clear()


def test_replaced_receiver_rejects_previous_game_output(tmp_path: Path) -> None:
    parent = QObject()
    feed = GameLanFeed(parent)
    old = feed.receiver("old", lambda _line: None, tmp_path / "old.log")
    previous_stop = feed._log_stop
    new = feed.receiver("new", lambda _line: None, tmp_path / "new.log")
    old("Started serving on 51234")
    assert feed.port == 0 and previous_stop.is_set()
    new("Started serving on 54321")
    assert (feed.instance_id, feed.port) == ("new", 54321)
    feed.clear()


def test_closed_window_does_not_leave_a_failing_log_thread(tmp_path: Path) -> None:
    parent = QObject()
    feed = GameLanFeed(parent)
    path = tmp_path / "latest.log"
    feed.receiver("chosen", lambda _line: None, path)
    feed.begin_session()
    delete(parent)
    path.write_text("Started serving on 54321\n")
    wait_until(feed._log_stop.is_set)
