"""Script tráo thư mục: chờ tiến trình cũ, đổi bản mới vào, mở lại; chép hỏng thì trả lại bản cũ."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from nostalgia.system.platform_info import CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW
from nostalgia.update.apply import (
    INSTALL_KIND_APPIMAGE,
    INSTALL_KIND_FROZEN,
    INSTALL_KIND_READONLY,
    INSTALL_KIND_SOURCE,
    SwapPlan,
    clean_child_env,
    detect_install_kind,
    launch_swap_script,
    render_swap_script,
    write_swap_script,
)

# Test script sh cần POSIX; test PowerShell cần powershell/pwsh. KHÔNG skip cả file:
# bug 1.0.15 sống sót được chính vì mọi test Windows đều bị skip trên máy dev Linux.
posix_only = pytest.mark.skipif(os.name == "nt", reason="script sh chỉ chạy trên POSIX")
_POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
needs_powershell = pytest.mark.skipif(
    _POWERSHELL is None, reason="máy không có powershell/pwsh để chạy script thật"
)


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


@posix_only
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


@posix_only
def test_failed_copy_restores_the_old_install(tmp_path: Path) -> None:
    install, _staged, marker = make_tree(tmp_path)
    missing_staged = tmp_path / "updates" / "khong-ton-tai"
    plan = SwapPlan(install, missing_staged, install / "nostalgia-ui", os.getpid() + 100_000)
    script = write_swap_script(plan, tmp_path / "scripts", windows=False)

    result = subprocess.run(["/bin/sh", str(script)], timeout=20)

    assert result.returncode == 1
    assert (install / "lib" / "core.so").read_text() == "cũ", "thất bại thì bản cũ phải nguyên"
    assert not marker.exists()


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


def _make_frozen_executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Giả một gói `frozen` (`sys.frozen=True`, `sys.executable` trỏ vào `tmp_path`)."""
    install_dir = tmp_path / "Nostalgia"
    install_dir.mkdir()
    executable = install_dir / "nostalgia-ui"
    executable.write_text("")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "platform", "linux")
    return install_dir


def test_appimage_env_blocks_swap_even_if_writable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JL-9: biến môi trường `APPIMAGE` báo mount squashfs chỉ-đọc — không tráo được dù
    `install_dir` (giả trong tmp_path) trông như ghi được."""
    _make_frozen_executable(tmp_path, monkeypatch)
    monkeypatch.setenv("APPIMAGE", "/tmp/.mount_Nostalgia/AppRun")

    assert detect_install_kind() == INSTALL_KIND_APPIMAGE


# Một điều kiện gộp: `os.geteuid` không tồn tại trên Windows, tách hai decorator là nổ
# ngay lúc pytest thu thập test trên runner Windows.
@pytest.mark.skipif(
    os.name == "nt" or os.geteuid() == 0,
    reason="chmod 0o555 cần POSIX, và root thì ghi được cả thư mục 0o555",
)
def test_readonly_install_dir_blocks_swap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """JL-9: `install_dir` không có quyền ghi (`.deb`/`.rpm` ở `/opt` chủ root) — không tráo
    được."""
    install_dir = _make_frozen_executable(tmp_path, monkeypatch)
    monkeypatch.delenv("APPIMAGE", raising=False)
    install_dir.chmod(0o555)
    try:
        assert detect_install_kind() == INSTALL_KIND_READONLY
    finally:
        install_dir.chmod(0o755)


def test_writable_frozen_install_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """JL-9: đường `frozen` bình thường (ghi được, không phải AppImage) không được đổi hành vi —
    đây là đường đang chạy tốt của đa số người dùng Linux/Windows."""
    _make_frozen_executable(tmp_path, monkeypatch)
    monkeypatch.delenv("APPIMAGE", raising=False)

    assert detect_install_kind() == INSTALL_KIND_FROZEN


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
