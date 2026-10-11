"""Log dồn trong lúc giao diện bị nghẽn không được giữ RAM tăng theo thời gian."""

from __future__ import annotations

import tracemalloc

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn")

from PySide6.QtTest import QAbstractItemModelTester

from nostalgia.ui.game_log import GameLogFeed, GameLogModel
from nostalgia.ui.game_log_buffer import MAX_LINE_CHARACTERS, MAX_LINES, MAX_LOG_CHARACTERS

pytestmark = pytest.mark.usefixtures("qt_app")


def test_stalled_interface_does_not_accumulate_the_entire_game_output() -> None:
    feed = GameLogFeed()
    tracemalloc.start()
    try:
        for number in range(20_000):
            feed.receive(f"{number}: " + "x" * 1024)
        _current, peak = tracemalloc.get_traced_memory()
        assert peak < MAX_LOG_CHARACTERS * 8, "bộ đệm chưa gom không được giữ 20 MB log"
    finally:
        tracemalloc.stop()
    feed.drain()
    assert feed.model.rowCount() <= MAX_LINES
    assert sum(map(len, feed.model.lines)) <= MAX_LOG_CHARACTERS
    assert feed.model.lines[-1].startswith("19999: ")
    assert feed.tail_snapshot[-1] == feed.model.lines[-1]


def test_long_unicode_lines_keep_the_latest_evidence_within_the_budget() -> None:
    feed = GameLogFeed()
    for number in range(400):
        feed.receive(f"java.lang.Error {number}: " + "😀" * 32_000 + f" crash-{number}")
        if number % 100 == 0:
            feed.drain()
    feed.drain()
    assert sum(map(len, feed.model.lines)) <= MAX_LOG_CHARACTERS
    assert all(len(line) <= MAX_LINE_CHARACTERS for line in feed.model.lines)
    assert all(len(line) <= MAX_LINE_CHARACTERS for line in feed.tail_snapshot)
    assert feed.model.lines[-1].startswith("java.lang.Error 399: ")
    assert feed.model.lines[-1].endswith(" crash-399")
    feed.reset()
    feed.receive("dòng đầu phiên mới")
    feed.begin_session()
    feed.end_session()
    assert feed.model.lines == ["dòng đầu phiên mới"]


def test_model_never_temporarily_inserts_a_batch_larger_than_the_budget() -> None:
    model = GameLogModel()
    tester = QAbstractItemModelTester(model, QAbstractItemModelTester.FailureReportingMode.Warning)
    peaks: list[int] = []
    model.rowsInserted.connect(lambda *_args: peaks.append(model.rowCount()))
    model.append_lines([f"old {number}" for number in range(MAX_LINES)])
    model.append_lines([f"new {number}" for number in range(MAX_LINES * 4)])
    assert max(peaks) <= MAX_LINES
    assert model.lines[0] == f"new {MAX_LINES * 3}"
    model.append_lines(["x" * 4096] * 400)
    assert sum(map(len, model.lines)) <= MAX_LOG_CHARACTERS
    assert tester.model() is model
