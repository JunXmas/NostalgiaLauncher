"""Script tráo PowerShell cho Windows — bản kế nhiệm của batch chết im lặng ở 1.0.15.

Ba đường chết của batch (timeout/t với stdin=DEVNULL, OEM codepage với đường dẫn có dấu,
move không retry khi Defender giữ file) đều có test gác ở đây; hai test cuối chạy script
THẬT bằng powershell/pwsh.
"""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import pytest
from test_update_apply import _POWERSHELL, needs_powershell

from nostalgia.system.platform_info import CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW
from nostalgia.update.apply import (
    INSTALL_KIND_SOURCE,
    SwapPlan,
    detect_install_kind,
    launch_swap_script,
    render_swap_script,
    write_swap_script,
)


def test_windows_launch_uses_powershell_no_window_not_detached_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JL-7 + bug 1.0.15: phải là `powershell.exe -File` (batch qua `cmd.exe` chết ở
    `timeout /t` khi stdin=DEVNULL và ở codepage với đường dẫn có dấu). Cờ vẫn là
    CREATE_NO_WINDOW thay DETACHED_PROCESS — dùng chung là Windows lờ CREATE_NO_WINDOW đi."""
    captured: dict[str, object] = {}

    def fake_popen(argv: list[str], **kwargs: object) -> None:
        captured["argv"] = argv
        captured["kwargs"] = kwargs

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    launch_swap_script(tmp_path / "apply-update.ps1", windows=True)

    argv = captured["argv"]
    assert isinstance(argv, list)
    assert argv[0] == "powershell.exe", "batch/cmd.exe là con đường của bug 1.0.15"
    assert "-NoProfile" in argv and "-File" in argv
    flags = captured["kwargs"]["creationflags"]  # type: ignore[index]
    assert flags == CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    assert flags & 0x00000008 == 0, "DETACHED_PROCESS (0x8) không được còn"


def _windows_plan() -> SwapPlan:
    # Đường dẫn có dấu tiếng Việt + khoảng trắng — đúng hình dạng cài mặc định
    # (C:\Users\<tên>\AppData\Local\Programs) làm bản batch 1.0.15 chết ở codepage.
    return SwapPlan(
        Path(r"C:\Users\Tuấn Anh\AppData\Local\Programs\Nostalgia"),
        Path(r"C:\Users\Tuấn Anh\AppData\Roaming\nostalgia\updates\1.1.1"),
        Path(r"C:\Users\Tuấn Anh\AppData\Local\Programs\Nostalgia\nostalgia-ui.exe"),
        4242,
    )


def test_windows_script_is_powershell_not_batch() -> None:
    script = render_swap_script(_windows_plan(), windows=True)
    assert "Wait-Process" not in script, "chờ bằng vòng Get-Process để có deadline"
    assert "Get-Process -Id 4242" in script
    assert "Start-Sleep" in script
    # Ba vết dao găm của bản batch — không được quay lại:
    assert "timeout /t" not in script, "timeout.exe chết khi stdin bị redirect"
    assert "xcopy" not in script and "@echo off" not in script
    assert "Move-Item" in script and "Copy-Item" in script
    assert "'C:\\Users\\Tuấn Anh\\AppData\\Local\\Programs\\Nostalgia'" in script
    assert detect_install_kind() == INSTALL_KIND_SOURCE, "test chạy từ mã nguồn, không phải gói"


def test_windows_script_retries_the_move_and_restores_on_failed_copy() -> None:
    """Defender giữ file exe vài giây sau khi tiến trình thoát → move phải thử lại;
    chép hỏng thì trả lại thư mục cũ — người dùng không bao giờ mất launcher."""
    script = render_swap_script(_windows_plan(), windows=True)
    assert "$try -lt 30" in script, "move phải có vòng thử lại"
    assert script.index("catch") < script.rindex("Move-Item"), "trong catch phải trả lại bản cũ"
    assert "exit 1" in script


def test_windows_script_written_with_bom(tmp_path: Path) -> None:
    """PowerShell 5.1 đọc file không BOM theo ANSI codepage — đường dẫn có dấu thành rác."""
    script_path = write_swap_script(_windows_plan(), tmp_path / "scripts", windows=True)
    assert script_path.name == "apply-update.ps1"
    raw = script_path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "thiếu BOM UTF-8"
    assert "Tuấn Anh" in raw.decode("utf-8-sig")


@needs_powershell
def test_powershell_swap_waits_replaces_and_restores(tmp_path: Path) -> None:
    """Chạy script THẬT bằng PowerShell (pwsh trên Linux CI, powershell trên Windows):
    chờ tiến trình, tráo thư mục, dọn bản cũ; và đường hỏng thì trả lại nguyên trạng."""
    assert _POWERSHELL is not None
    install = tmp_path / "Nostalgia thử ứ"  # khoảng trắng + dấu: đúng chỗ batch cũ chết
    staged = tmp_path / "updates" / "1.1.1"
    for directory, body in ((install, "cũ"), (staged, "mới")):
        (directory / "lib").mkdir(parents=True)
        (directory / "lib" / "core.dll").write_text(body, encoding="utf-8")
        (directory / "nostalgia-ui.exe").write_text("", encoding="utf-8")

    sleeper = subprocess.Popen(
        [_POWERSHELL, "-NoProfile", "-Command", "Start-Sleep -Milliseconds 300"]
    )
    threading.Thread(target=sleeper.wait, daemon=True).start()
    plan = SwapPlan(install, staged, install / "nostalgia-ui.exe", sleeper.pid)
    # Start-Process cuối script sẽ fail (file .exe rỗng không chạy được trên Linux) — cắt
    # dòng đó đi: điều test gác là CHỜ + TRÁO + DỌN, việc mở lại đã có test render gác chữ.
    script = "\n".join(
        line
        for line in render_swap_script(plan, windows=True).splitlines()
        if not line.startswith("Start-Process")
    )
    script_path = tmp_path / "apply-update.ps1"
    script_path.write_text(script, encoding="utf-8-sig")

    subprocess.run(
        [_POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        check=True,
        timeout=60,
    )

    assert (install / "lib" / "core.dll").read_text(encoding="utf-8") == "mới"
    assert not install.with_name(install.name + ".old").exists(), "bản cũ phải được dọn"
    assert staged.is_dir(), "bản bung vẫn còn để lần sau không tải lại nếu cần"


@needs_powershell
def test_powershell_failed_copy_restores_the_old_install(tmp_path: Path) -> None:
    assert _POWERSHELL is not None
    install = tmp_path / "Nostalgia"
    (install / "lib").mkdir(parents=True)
    (install / "lib" / "core.dll").write_text("cũ", encoding="utf-8")
    missing_staged = tmp_path / "updates" / "khong-ton-tai"
    plan = SwapPlan(install, missing_staged, install / "nostalgia-ui.exe", os.getpid() + 100_000)
    script_path = tmp_path / "apply-update.ps1"
    script_path.write_text(render_swap_script(plan, windows=True), encoding="utf-8-sig")

    result = subprocess.run(
        [_POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        timeout=60,
    )

    assert result.returncode == 1
    assert (install / "lib" / "core.dll").read_text(encoding="utf-8") == "cũ", (
        "thất bại thì bản cũ phải nguyên"
    )
