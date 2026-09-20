"""Script tráo thư mục: chờ tiến trình cũ, đổi bản mới vào, mở lại; chép hỏng thì trả lại bản cũ."""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path

import pytest

from nostalgia.system.platform_info import CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW
from nostalgia.update.apply import (
    INSTALL_KIND_SOURCE,
    SwapPlan,
    clean_child_env,
    detect_install_kind,
    launch_swap_script,
    render_swap_script,
    write_swap_script,
)

pytestmark = pytest.mark.skipif(os.name == "nt", reason="script sh chỉ chạy trên POSIX")


def make_tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    install = tmp_path / "Nostalgia"
    staged = tmp_path / "updates" / "0.2.0"
    for directory, body in ((install, "cũ"), (staged, "mới")):
        (directory / "lib").mkdir(parents=True)
        (directory / "lib" / "core.so").write_text(body)
    marker = tmp_path / "relaunched.txt"
    for directory in (install, staged):
        (directory / "nostalgia-ui").write_text(f"#!/bin/sh\necho started > '{marker}'\n")
        (directory / "nostalgia-ui").chmod(0o755)
    return install, staged, marker


def test_swap_waits_for_the_old_process_then_replaces_and_relaunches(tmp_path: Path) -> None:
    install, staged, marker = make_tree(tmp_path)
    sleeper = subprocess.Popen(["sleep", "0.3"])
    # Thu dọn tiến trình khi nó thoát (ngoài đời init làm việc này); zombie vẫn trả lời kill -0.
    threading.Thread(target=sleeper.wait, daemon=True).start()
    plan = SwapPlan(install, staged, install / "nostalgia-ui", sleeper.pid)
    script = write_swap_script(plan, tmp_path / "scripts", windows=False)

    subprocess.run(["/bin/sh", str(script)], check=True, timeout=20)

    assert (install / "lib" / "core.so").read_text() == "mới"
    assert not install.with_name("Nostalgia.old").exists(), "bản cũ được dọn sau khi tráo xong"
    # nohup ... & khiến launcher chạy nền — chờ marker tối đa 5 giây.
    for _ in range(50):
        if marker.exists():
            break
        time.sleep(0.1)
    assert marker.exists() and marker.read_text().strip() == "started", "launcher mới được mở lại"
    assert staged.is_dir(), "bản bung vẫn còn để lần sau không tải lại nếu cần"


def test_failed_copy_restores_the_old_install(tmp_path: Path) -> None:
    install, _staged, marker = make_tree(tmp_path)
    missing_staged = tmp_path / "updates" / "khong-ton-tai"
    plan = SwapPlan(install, missing_staged, install / "nostalgia-ui", os.getpid() + 100_000)
    script = write_swap_script(plan, tmp_path / "scripts", windows=False)

    result = subprocess.run(["/bin/sh", str(script)], timeout=20)

    assert result.returncode == 1
    assert (install / "lib" / "core.so").read_text() == "cũ", "thất bại thì bản cũ phải nguyên"
    assert not marker.exists()


def test_windows_launch_uses_create_no_window_not_detached_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JL-7: DETACHED_PROCESS không ẩn được console của `cmd.exe` (nó tự AllocConsole) và làm
    CREATE_NO_WINDOW bị Windows lờ đi khi dùng chung — phải thay cờ, không phải thêm."""
    captured: dict[str, object] = {}

    def fake_popen(argv: list[str], **kwargs: object) -> None:
        captured["argv"] = argv
        captured["kwargs"] = kwargs

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    launch_swap_script(tmp_path / "apply-update.cmd", windows=True)

    flags = captured["kwargs"]["creationflags"]  # type: ignore[index]
    assert flags == CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    assert flags & 0x00000008 == 0, "DETACHED_PROCESS (0x8) không được còn"


def test_windows_script_and_source_install_kind() -> None:
    plan = SwapPlan(
        Path(r"C:\Nostalgia"),
        Path(r"C:\Data\updates\0.2.0"),
        Path(r"C:\Nostalgia\nostalgia-ui.exe"),
        4242,
    )
    script = render_swap_script(plan, windows=True)
    assert "tasklist" in script and "4242" in script and "xcopy" in script
    assert 'move "C:\\Nostalgia.old" "C:\\Nostalgia"' in script, "chép hỏng thì trả lại"
    assert detect_install_kind() == INSTALL_KIND_SOURCE, "test chạy từ mã nguồn, không phải gói"


def test_sh_script_uses_nohup_not_exec() -> None:
    """Script sh phải dùng ``nohup ... &`` thay vì ``exec`` để launcher mới
    không bị kẹt trong session bị cô lập."""
    plan = SwapPlan(
        Path("/opt/Nostalgia"), Path("/tmp/staged"), Path("/opt/Nostalgia/nostalgia-ui"), 1234
    )
    script = render_swap_script(plan, windows=False)
    assert "nohup" in script, "phải dùng nohup"
    assert "exec " not in script, "không được dùng exec — kẹt session cô lập"


def test_clean_child_env_restores_orig(monkeypatch: pytest.MonkeyPatch) -> None:
    """Khi PyInstaller đặt ``LD_LIBRARY_PATH_ORIG``, ``clean_child_env`` phải
    khôi phục giá trị gốc đó và xoá biến ``_ORIG``."""
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEIxxxxxx/lib")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/usr/lib")
    env = clean_child_env()
    assert env["LD_LIBRARY_PATH"] == "/usr/lib"
    assert "LD_LIBRARY_PATH_ORIG" not in env


def test_clean_child_env_removes_when_no_orig(monkeypatch: pytest.MonkeyPatch) -> None:
    """Khi không có ``_ORIG``, biến bị ô nhiễm phải bị xoá hoàn toàn."""
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/_MEIxxxxxx/lib")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    env = clean_child_env()
    assert "LD_LIBRARY_PATH" not in env
