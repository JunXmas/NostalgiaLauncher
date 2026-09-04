"""Chạy và dừng game. Thay Java bằng một script Python con — nhanh, và kiểm được y hệt."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from nostalgia.launch.command import LaunchCommand
from nostalgia.launch.game_process import (
    SINGLE_PROCESS,
    WHOLE_GROUP,
    resolve_signal_target,
    start_game,
)

# Hạn ngắn để bộ test không mất vài giây mỗi lần dừng. Giá trị thật nằm ở hằng của module.
GRACE = 0.3
DEADLINE = 6.0


def python_command(tmp_path: Path, source: str, *arguments: str) -> LaunchCommand:
    """Dựng lệnh chạy một script Python. `main_class` chính là đường dẫn script."""
    script = tmp_path / "gia_lap_game.py"
    script.write_text(source, encoding="utf-8")
    return LaunchCommand(
        java_binary=Path(sys.executable),
        jvm_arguments=(),
        main_class=str(script),
        game_arguments=arguments,
        game_dir=tmp_path / "game",
    )


def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def wait_until_dead(pid: int, deadline_seconds: float = DEADLINE) -> float:
    """Trả về thời gian chờ thật. Vòng lặp CÓ HẠN — không bao giờ chờ mãi."""
    started = time.monotonic()
    while time.monotonic() - started < deadline_seconds:
        if not is_alive(pid):
            return time.monotonic() - started
        time.sleep(0.02)
    return float("inf")


def test_output_is_captured_line_by_line_and_the_exit_code_comes_back(tmp_path: Path) -> None:
    command = python_command(
        tmp_path, "import sys\nprint('dong mot')\nprint('dong hai')\nsys.exit(3)\n"
    )
    lines: list[str] = []

    game = start_game(command, on_output=lines.append)
    exit_code = game.wait(timeout=DEADLINE)

    assert exit_code == 3
    assert lines == ["dong mot", "dong hai"]
    assert not game.is_running
    assert game.exit_code == 3


def test_the_game_runs_inside_the_game_directory_and_it_is_created(tmp_path: Path) -> None:
    command = python_command(tmp_path, "import os\nprint(os.getcwd())\n")
    lines: list[str] = []

    start_game(command, on_output=lines.append).wait(timeout=DEADLINE)

    assert Path(lines[0]).resolve() == command.game_dir.resolve()


def test_output_that_is_not_utf8_does_not_kill_the_reader(tmp_path: Path) -> None:
    """Log của game có thể chứa byte lạ từ tên file hay từ thư viện của mod."""
    command = python_command(
        tmp_path,
        "import sys\nsys.stdout.buffer.write(b'truoc \\xff\\xfe sau\\n')\n"
        "sys.stdout.buffer.write(b'van con dong nay\\n')\n",
    )
    lines: list[str] = []

    start_game(command, on_output=lines.append).wait(timeout=DEADLINE)

    assert len(lines) == 2, "mất dòng sau nghĩa là luồng đọc đã chết giữa chừng"
    assert "truoc" in lines[0] and "sau" in lines[0]
    assert lines[1] == "van con dong nay"


def test_the_game_gets_its_own_process_group(tmp_path: Path) -> None:
    """Đây là điều kiện để `killpg` an toàn: game phải là trưởng nhóm phiên riêng."""
    command = python_command(tmp_path, "import time\ntime.sleep(30)\n")

    game = start_game(command)
    try:
        assert os.getpgid(game.pid) == game.pid
        assert os.getpgid(game.pid) != os.getpgid(os.getpid())
    finally:
        game.stop(grace_seconds=GRACE)


def test_stopping_kills_the_grandchildren_too(tmp_path: Path) -> None:
    """Minecraft đẻ tiến trình con; bỏ sót là để lại java chạy ngầm ăn hết CPU."""
    pid_file = tmp_path / "chau.pid"
    command = python_command(
        tmp_path,
        "import subprocess, sys, time\n"
        f"chau = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(pid_file)!r}, 'w').write(str(chau.pid))\n"
        "time.sleep(60)\n",
    )

    game = start_game(command)
    for _ in range(300):
        if pid_file.exists() and pid_file.read_text():
            break
        time.sleep(0.02)
    grandchild_pid = int(pid_file.read_text())
    assert is_alive(grandchild_pid)

    started = time.monotonic()
    game.stop(grace_seconds=GRACE)
    elapsed = time.monotonic() - started

    assert not game.is_running
    assert wait_until_dead(grandchild_pid) < DEADLINE, "cháu nội còn sống sau khi dừng"
    assert elapsed < DEADLINE


def test_stopping_never_touches_the_launchers_own_process_group(tmp_path: Path) -> None:
    """Nếu `killpg` bắn nhầm nhóm, chính bộ test này chết — nên kiểm cả nhóm lẫn tiến trình."""
    own_group = os.getpgid(os.getpid())
    command = python_command(tmp_path, "import time\ntime.sleep(30)\n")

    game = start_game(command)
    game.stop(grace_seconds=GRACE)

    assert os.getpgid(os.getpid()) == own_group
    assert is_alive(os.getpid())


def test_a_process_that_ignores_sigterm_is_killed_anyway(tmp_path: Path) -> None:
    command = python_command(
        tmp_path,
        "import signal, sys, time\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "print('san sang', flush=True)\n"
        "time.sleep(60)\n",
    )
    lines: list[str] = []

    game = start_game(command, on_output=lines.append)
    for _ in range(300):
        if lines:
            break
        time.sleep(0.02)

    started = time.monotonic()
    exit_code = game.stop(grace_seconds=GRACE)

    assert time.monotonic() - started < DEADLINE
    assert not game.is_running
    assert exit_code == -signal.SIGKILL


def test_a_grandchild_holding_the_pipe_does_not_hang_the_wait(tmp_path: Path) -> None:
    """Cháu nội giữ `stdout` thì luồng đọc không bao giờ thấy EOF. `wait` vẫn phải trả về."""
    command = python_command(
        tmp_path,
        "import subprocess, sys\n"
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "print('cha thoat ngay', flush=True)\n",
    )

    game = start_game(command)
    started = time.monotonic()
    exit_code = game.wait(timeout=DEADLINE)
    elapsed = time.monotonic() - started

    assert exit_code == 0
    assert elapsed < DEADLINE, "chờ EOF của ống là treo vĩnh viễn"
    game.stop(grace_seconds=GRACE)


def test_stopping_an_already_finished_game_is_harmless(tmp_path: Path) -> None:
    command = python_command(tmp_path, "import sys\nsys.exit(7)\n")

    game = start_game(command)
    assert game.wait(timeout=DEADLINE) == 7

    assert game.stop(grace_seconds=GRACE) == 7
    assert game.stop(grace_seconds=GRACE) == 7, "gọi nhiều lần vẫn phải yên"


def test_waiting_past_the_timeout_raises_instead_of_blocking_forever(tmp_path: Path) -> None:
    command = python_command(tmp_path, "import time\ntime.sleep(30)\n")

    game = start_game(command)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            game.wait(timeout=0.2)
        assert game.is_running
    finally:
        game.stop(grace_seconds=GRACE)


def test_a_handler_that_raises_does_not_take_the_reader_down(tmp_path: Path) -> None:
    """Người gọi viết `on_output`; lỗi của họ không được làm mất log của người dùng."""
    command = python_command(tmp_path, "print('a')\nprint('b')\n")
    seen: list[str] = []

    def explode(line: str) -> None:
        seen.append(line)
        raise RuntimeError("lỗi của người gọi")

    game = start_game(command, on_output=explode)
    assert game.wait(timeout=DEADLINE) == 0
    assert seen == ["a", "b"]


def test_the_environment_can_be_replaced_for_isolation(tmp_path: Path) -> None:
    """Cần cho test và cho chế độ chạy di động: không để lộ biến môi trường thật vào game."""
    command = python_command(tmp_path, "import os\nprint(os.environ.get('DANH_DAU', 'khong'))\n")
    lines: list[str] = []

    start_game(command, on_output=lines.append, environment={"DANH_DAU": "co"}).wait(
        timeout=DEADLINE
    )

    assert lines == ["co"]


def test_stderr_is_captured_too(tmp_path: Path) -> None:
    """Báo cáo sập của Java đi ra stderr — mất nó là mất đúng thứ cần nhất khi gỡ lỗi."""
    command = python_command(
        tmp_path, "import sys\nprint('ra stdout')\nprint('ra stderr', file=sys.stderr)\n"
    )
    lines: list[str] = []

    start_game(command, on_output=lines.append).wait(timeout=DEADLINE)

    assert sorted(lines) == ["ra stderr", "ra stdout"]


def test_stopping_a_finished_game_sends_no_signal_at_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pid của tiến trình đã thu dọn có thể được cấp lại cho chương trình khác.

    Giả lập đúng tình huống đó: `getpgid` trả về như thể pid vẫn sống và là trưởng nhóm.
    Nếu `stop()` không thoát sớm nhờ mã thoát đã có, nó sẽ bắn tín hiệu vào nhóm của một
    chương trình chẳng liên quan gì.
    """
    game = start_game(python_command(tmp_path, "import sys\nsys.exit(0)\n"))
    assert game.wait(timeout=DEADLINE) == 0

    sent: list[tuple[str, int]] = []
    monkeypatch.setattr(os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(os, "kill", lambda pid, _sig: sent.append(("kill", pid)))
    monkeypatch.setattr(os, "killpg", lambda pgid, _sig: sent.append(("killpg", pgid)))

    game.stop(grace_seconds=GRACE)

    assert sent == []


def test_only_a_process_group_leader_may_be_killed_as_a_group() -> None:
    """Quyết định an toàn nhất của module, kiểm thẳng — gửi tín hiệu thật để kiểm điều này
    nghĩa là cố tình bắn vào nhóm đang chạy chính bộ test."""
    assert resolve_signal_target(4321, 4321) == (WHOLE_GROUP, 4321)
    assert resolve_signal_target(4321, 999) == (SINGLE_PROCESS, 4321)
    assert resolve_signal_target(4321, os.getpgid(os.getpid())) == (SINGLE_PROCESS, 4321)
