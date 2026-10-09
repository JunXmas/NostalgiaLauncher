"""Cờ rảnh chỉ đổi trên luồng Qt, sau kết quả/error đã được giao tới giao diện."""

import threading
from collections.abc import Callable

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Signal, Slot
from test_bridges import wait_until

from nostalgia.errors import NostalgiaError
from nostalgia.ui.worker import WorkerBridge, wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


class CompletionProbe(WorkerBridge):
    result = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.observed: list[tuple[str, bool, int]] = []
        self.follow_up: Callable[[], None] | None = None
        self.result.connect(self._result_received)
        self.failed.connect(self._error_received)
        self.busyChanged.connect(self._busy_changed)

    @Slot()
    def _result_received(self) -> None:
        self.observed.append(("result", bool(self.busy), threading.get_ident()))
        if self.follow_up is not None:
            self.run_in_background(self.follow_up)

    @Slot(str)
    def _error_received(self, _message: str) -> None:
        self.observed.append(("error", bool(self.busy), threading.get_ident()))

    @Slot()
    def _busy_changed(self) -> None:
        self.observed.append(("busy", bool(self.busy), threading.get_ident()))


@pytest.mark.parametrize("fail", [False, True])
def test_worker_keeps_busy_until_queued_result_is_delivered(fail: bool) -> None:
    worker = CompletionProbe()
    ui_thread = threading.get_ident()

    def work() -> None:
        if fail:
            raise NostalgiaError("expected fixture error")
        worker.result.emit()

    worker.run_in_background(work)
    wait_for_background()
    # Không xử lý event Qt: luồng đã xong nhưng kết quả vẫn chờ UI nhận.
    assert worker.busy
    wait_until(lambda: not worker.busy, seconds=2)
    assert worker.observed == [
        ("busy", True, ui_thread),
        ("error" if fail else "result", True, ui_thread),
        ("busy", False, ui_thread),
    ]


def test_finishing_previous_request_does_not_clear_follow_up_busy_state() -> None:
    worker = CompletionProbe()
    entered, release = threading.Event(), threading.Event()

    def follow_up() -> None:
        entered.set()
        assert release.wait(3)

    worker.follow_up = follow_up
    try:
        worker.run_in_background(worker.result.emit)
        wait_for_background()
        wait_until(entered.is_set)
        assert worker.busy
        release.set()
        wait_until(lambda: not worker.busy)
        assert worker.observed[-1][0:2] == ("busy", False)
    finally:
        release.set()
        wait_for_background()
