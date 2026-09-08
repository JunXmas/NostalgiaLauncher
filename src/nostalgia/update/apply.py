"""Áp bản mới đã bung: chỉ làm được khi launcher chạy từ gói đóng sẵn (PyInstaller, `sys.frozen`).

Không thể tự ghi đè chính mình trong lúc đang chạy (Windows khoá file, Linux thì file đang
mở), nên launcher viết một script tráo thư mục rồi thoát; script chờ tiến trình cũ tắt, đổi
`install` → `install.old`, chép bản mới vào, xoá bản cũ, mở launcher mới. Chép hỏng thì trả
lại thư mục cũ — người dùng không bao giờ bị mất launcher.

Chạy từ mã nguồn (`uv run nostalgia-ui`) thì không áp được: cập nhật là việc của `git pull`
+ `uv sync`; ở đây chỉ nói rõ điều đó.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from nostalgia.storage.files import ensure_dir, set_executable

INSTALL_KIND_FROZEN = "frozen"
INSTALL_KIND_SOURCE = "source"
EXECUTABLE_NAME = "nostalgia-ui"


@dataclass(frozen=True, slots=True)
class SwapPlan:
    """Mọi thứ script tráo cần biết. Thuần dữ liệu để test không phải chạy script thật."""

    install_dir: Path
    staged_dir: Path
    executable: Path
    wait_pid: int


def detect_install_kind() -> str:
    return INSTALL_KIND_FROZEN if getattr(sys, "frozen", False) else INSTALL_KIND_SOURCE


def current_install_dir() -> Path:
    """Thư mục chứa launcher đang chạy (gói onedir của PyInstaller)."""
    return Path(sys.executable).resolve().parent


def render_swap_script(plan: SwapPlan, *, windows: bool = os.name == "nt") -> str:
    """Nội dung script tráo thư mục cho hệ đang chạy."""
    if windows:
        return _render_cmd(plan)
    return _render_sh(plan)


def write_swap_script(
    plan: SwapPlan, scripts_dir: Path, *, windows: bool = os.name == "nt"
) -> Path:
    ensure_dir(scripts_dir)
    script_path = scripts_dir / ("apply-update.cmd" if windows else "apply-update.sh")
    script_path.write_text(render_swap_script(plan, windows=windows), encoding="utf-8")
    if not windows:
        set_executable(script_path)
    return script_path


def launch_swap_script(script_path: Path, *, windows: bool = os.name == "nt") -> None:
    """Chạy script tách hẳn khỏi launcher, để launcher thoát mà script vẫn sống."""
    if windows:
        detached = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            ["cmd.exe", "/c", str(script_path)], creationflags=detached, close_fds=True
        )
        return
    subprocess.Popen(
        ["/bin/sh", str(script_path)],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def _render_sh(plan: SwapPlan) -> str:
    install, staged = _quote(plan.install_dir), _quote(plan.staged_dir)
    old = _quote(plan.install_dir.with_name(plan.install_dir.name + ".old"))
    executable = _quote(plan.executable)
    return f"""#!/bin/sh
# Nostalgia Launcher — tráo bản mới sau khi launcher cũ thoát. Tự sinh, đừng sửa tay.
set -u
tries=0
while kill -0 {plan.wait_pid} 2>/dev/null; do
    tries=$((tries + 1)); [ "$tries" -gt 600 ] && exit 1
    sleep 0.1
done
rm -rf {old}
mv {install} {old} || exit 1
if cp -R {staged} {install}; then
    rm -rf {old}
else
    rm -rf {install}; mv {old} {install}; exit 1
fi
exec {executable}
"""


def _render_cmd(plan: SwapPlan) -> str:
    install, staged = str(plan.install_dir), str(plan.staged_dir)
    old = str(plan.install_dir.with_name(plan.install_dir.name + ".old"))
    return f"""@echo off
rem Nostalgia Launcher — tráo bản mới sau khi launcher cũ thoát. Tự sinh, đừng sửa tay.
set tries=0
:wait
tasklist /FI "PID eq {plan.wait_pid}" 2>nul | find "{plan.wait_pid}" >nul
if not errorlevel 1 (
    set /a tries+=1
    if %tries% gtr 600 exit /b 1
    timeout /t 1 /nobreak >nul
    goto wait
)
if exist "{old}" rmdir /s /q "{old}"
move "{install}" "{old}" || exit /b 1
xcopy "{staged}" "{install}\\" /E /I /H /Y >nul
if errorlevel 1 (
    rmdir /s /q "{install}"
    move "{old}" "{install}"
    exit /b 1
)
rmdir /s /q "{old}"
start "" "{plan.executable}"
"""


def _quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\\''") + "'"
