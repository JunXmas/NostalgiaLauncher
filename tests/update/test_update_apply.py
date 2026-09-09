"""Script tráo thư mục: chờ tiến trình cũ, đổi bản mới vào, mở lại; chép hỏng thì trả lại bản cũ."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import pytest

from nostalgia.update.apply import (
    INSTALL_KIND_SOURCE,
    SwapPlan,
    detect_install_kind,
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
    assert marker.read_text().strip() == "started", "launcher mới được mở lại"
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
