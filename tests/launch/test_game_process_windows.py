"""LAU-01: kiểm nhánh Windows của game_process — dừng game không dùng POSIX process group."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from test_game_process import DEADLINE, GRACE, python_command

from nostalgia.launch.game_process import (
    CREATE_NEW_PROCESS_GROUP,
    CREATE_NO_WINDOW,
    resolve_creation_flags,
    start_game,
)


def test_windows_creation_flags_hide_console() -> None:
    """MYLA-37.5: trên Windows phải có CREATE_NO_WINDOW, nếu không `java.exe` mở cửa sổ CMD
    và người dùng đóng cửa sổ đó là Minecraft tắt theo. Giữ cả CREATE_NEW_PROCESS_GROUP."""
    flags = resolve_creation_flags("win32")
    assert flags & CREATE_NO_WINDOW
    assert flags & CREATE_NEW_PROCESS_GROUP


def test_posix_creation_flags_are_zero() -> None:
    """Ngoài Windows, `creationflags` phải là 0 — Popen từ chối mọi giá trị khác."""
    assert resolve_creation_flags("linux") == 0
    assert resolve_creation_flags("darwin") == 0


def test_windows_stop_uses_terminate_then_kill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LAU-01: trên Windows, ``stop()`` phải dùng ``terminate()``/``kill()`` thay vì
    ``os.getpgid``/``os.killpg`` — hai hàm đó không tồn tại trên Windows."""
    command = python_command(tmp_path, "import time\ntime.sleep(30)\n")
    game = start_game(command)

    # Giả lập nhánh Windows bằng cách vá sys.platform. Tiến trình con vẫn chạy bình thường
    # trên Linux — ta chỉ kiểm đường đi qua _stop_windows thay vì _stop_posix.
    monkeypatch.setattr(sys, "platform", "win32")

    started = time.monotonic()
    game.stop(grace_seconds=GRACE)
    elapsed = time.monotonic() - started

    assert not game.is_running
    assert elapsed < DEADLINE


def test_windows_stop_on_already_finished_game(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LAU-01: ``stop()`` trên Windows khi game đã thoát vẫn phải vô hại."""
    command = python_command(tmp_path, "import sys\nsys.exit(5)\n")
    game = start_game(command)
    assert game.wait(timeout=DEADLINE) == 5

    monkeypatch.setattr(sys, "platform", "win32")
    assert game.stop(grace_seconds=GRACE) == 5
