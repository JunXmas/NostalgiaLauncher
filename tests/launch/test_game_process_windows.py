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
    creation_flags_for,
    start_game,
)


def test_windows_hides_the_java_console_window() -> None:
    """MYLA-37: thiếu ``CREATE_NO_WINDOW`` thì Windows cấp cho ``java.exe`` một cửa sổ console
    riêng, và đóng cửa sổ đó là Minecraft tắt theo — đúng lỗi người dùng báo.

    Kiểm hàm thuần nên chạy được trên CI Linux, không cần máy Windows thật.
    """
    flags = creation_flags_for("win32")

    assert flags & CREATE_NO_WINDOW, "thiếu CREATE_NO_WINDOW: java.exe sẽ mở cửa sổ CMD"
    assert flags & CREATE_NEW_PROCESS_GROUP, "vẫn phải giữ nhóm tiến trình riêng"


def test_other_platforms_pass_no_creation_flags() -> None:
    """Cờ ``CreateProcess`` chỉ Windows hiểu; nơi khác phải là 0 đúng như trước."""
    assert creation_flags_for("linux") == 0
    assert creation_flags_for("darwin") == 0


def test_start_game_hands_the_flags_to_popen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hàm thuần đúng chưa đủ — phải chắc ``start_game`` THẬT SỰ truyền cờ xuống ``Popen``.

    Chặn ngay ``Popen`` thay vì chạy tiến trình thật: trên Linux mà truyền
    ``creationflags`` khác 0 là ``ValueError``, nên đây là cách duy nhất soi được nhánh
    Windows mà không cần máy Windows.
    """
    seen: dict[str, object] = {}

    class FakePopen:
        def __init__(self, _argv: object, **kwargs: object) -> None:
            seen.update(kwargs)
            self.stdout = None
            self.pid = 4242

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("nostalgia.launch.game_process.subprocess.Popen", FakePopen)

    start_game(python_command(tmp_path, "pass\n"))

    assert seen["creationflags"] == CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    assert seen["start_new_session"] is False, "Windows không có phiên POSIX"


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
