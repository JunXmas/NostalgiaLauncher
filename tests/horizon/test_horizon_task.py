"""Tác vụ chuẩn bị dừng được, không để process kẹt hoặc output tràn bộ nhớ."""

import sys
import threading
import time
from pathlib import Path

import pytest

from nostalgia.errors import Cancelled, InstanceError
from nostalgia.horizon.command import HorizonCommand
from nostalgia.horizon.process import run_horizon_task
from nostalgia.operations.cancellation import CancelToken


def test_native_task_captures_bounded_output_and_exit_status(tmp_path: Path) -> None:
    command = HorizonCommand(
        (sys.executable, "-c", "print('x'*2000); print('last'); exit(2)"), tmp_path
    )
    report = run_horizon_task(command, timeout_seconds=5)
    assert report.exit_code == 2
    assert report.tail[-1] == "last"
    assert len(report.tail[0]) == 1000


def test_cancelling_a_running_preparation_stops_it_promptly(tmp_path: Path) -> None:
    cancel_token = CancelToken()
    command = HorizonCommand((sys.executable, "-c", "import time; time.sleep(30)"), tmp_path)
    timer = threading.Timer(0.2, cancel_token.cancel)
    timer.start()
    started_at = time.monotonic()
    try:
        with pytest.raises(Cancelled):
            run_horizon_task(command, cancel_token=cancel_token)
    finally:
        timer.cancel()
    assert time.monotonic() - started_at < 6


def test_preparation_timeout_is_bounded(tmp_path: Path) -> None:
    command = HorizonCommand((sys.executable, "-c", "import time; time.sleep(30)"), tmp_path)
    started_at = time.monotonic()
    with pytest.raises(InstanceError, match="timed out"):
        run_horizon_task(command, timeout_seconds=0.1)
    assert time.monotonic() - started_at < 6
