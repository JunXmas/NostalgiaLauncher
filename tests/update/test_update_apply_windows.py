"""Script tráo PowerShell cho Windows — bản kế nhiệm của batch chết im lặng ở 1.0.15.

Ba đường chết của batch (timeout/t với stdin=DEVNULL, OEM codepage với đường dẫn có dấu,
move không retry khi Defender giữ file) đều có test gác ở đây; hai test cuối chạy script
THẬT bằng powershell/pwsh.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
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
    swap_log_path,
    write_swap_script,
)

windows_only = pytest.mark.skipif(
    os.name != "nt", reason="chỉ Windows mới khoá thư mục làm việc của tiến trình"
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


def test_windows_launch_sets_cwd_outside_the_install_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bug "tắt rồi không mở lại": thiếu `cwd=` thì script kế thừa thư mục làm việc của
    launcher, mà lối tắt Inno không đặt WorkingDir nên đó chính là THƯ MỤC CÀI. Windows giữ
    handle chặn DELETE trên cwd của tiến trình sống → Move-Item thư mục cài "Access denied"
    mãi mãi, vòng thử lại 30 giây không cứu được vì nguyên nhân không tự hết."""
    captured: dict[str, object] = {}

    def fake_popen(_argv: list[str], **kwargs: object) -> None:
        captured["kwargs"] = kwargs

    monkeypatch.setattr(subprocess, "Popen", fake_popen)

    launch_swap_script(tmp_path / "apply-update.ps1", windows=True)

    cwd = captured["kwargs"]["cwd"]  # type: ignore[index]
    assert cwd is not None, "thiếu cwd= là tái hiện đúng bug khoá thư mục"
    assert Path(cwd) == Path(tempfile.gettempdir())


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
    # `.strip()` vì lệnh nay nằm trong khối try nên có thụt lề; so với dòng chưa strip thì
    # bộ lọc trượt và test đỏ vì `.exe` rỗng chứ không vì điều nó định gác.
    script = "\n".join(
        line
        for line in render_swap_script(plan, windows=True).splitlines()
        if not line.strip().startswith("Start-Process")
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


@windows_only
@needs_powershell
def test_powershell_swaps_even_when_launched_from_inside_the_install_dir(
    tmp_path: Path,
) -> None:
    """Tái hiện ĐÚNG bug "tắt rồi không mở lại", trên Windows thật.

    Launcher cài bằng Inno; lối tắt không đặt WorkingDir nên Windows cho tiến trình cwd =
    thư mục cài. Test này spawn PowerShell với `cwd=install` — đúng thứ launcher hỏng đã
    làm. Trước bản vá, `Set-Location` không có và `Move-Item` ném "Access denied" 30 lần
    rồi exit 1: launcher đã thoát, không ai mở lại.

    Chỉ chạy trên Windows: Linux/macOS KHÔNG khoá thư mục theo cwd, nên trên máy dev test
    này xanh dù có vá hay không — chạy ở đó là tự lừa mình. Job `check-windows-updater`
    trong ci.yml là chỗ nó thực sự gác.
    """
    assert _POWERSHELL is not None
    install = tmp_path / "Nostalgia thử ứ"
    staged = tmp_path / "updates" / "1.1.3"
    for directory, body in ((install, "cũ"), (staged, "mới")):
        (directory / "lib").mkdir(parents=True)
        (directory / "lib" / "core.dll").write_text(body, encoding="utf-8")
        (directory / "nostalgia-ui.exe").write_text("", encoding="utf-8")

    plan = SwapPlan(install, staged, install / "nostalgia-ui.exe", os.getpid() + 100_000)
    script = "\n".join(
        line
        for line in render_swap_script(plan, windows=True).splitlines()
        if not line.startswith("    Start-Process")
    )
    script_path = tmp_path / "apply-update.ps1"
    script_path.write_text(script, encoding="utf-8-sig")

    result = subprocess.run(
        [_POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        cwd=install,  # <- đúng điều kiện làm launcher thật chết
        timeout=90,
    )

    # Dán nhật ký vào lời báo lỗi: job này chạy trên runner Windows nên không ai gỡ tay được,
    # mà "assert 1 == 0" một mình thì không nói script chết ở bước nào. Chính cái mù đó làm
    # bug sống qua nhiều bản.
    log = swap_log_path(script_path)
    diary = log.read_text(encoding="utf-8") if log.exists() else "(không có nhật ký)"
    assert result.returncode == 0, f"cwd trong thư mục cài vẫn phải tráo được. Nhật ký:\n{diary}"
    assert (install / "lib" / "core.dll").read_text(encoding="utf-8") == "mới"


@needs_powershell
def test_powershell_script_logs_what_it_did(tmp_path: Path) -> None:
    """Script chạy sau khi launcher thoát, stdout/stderr đều DEVNULL. Không có nhật ký thì
    lần hỏng sau lại phải đoán từ triệu chứng — đúng cách bug này sống sót nhiều bản."""
    assert _POWERSHELL is not None
    install = tmp_path / "Nostalgia"
    (install / "lib").mkdir(parents=True)
    (install / "lib" / "core.dll").write_text("cũ", encoding="utf-8")
    missing_staged = tmp_path / "updates" / "khong-ton-tai"
    plan = SwapPlan(install, missing_staged, install / "nostalgia-ui.exe", os.getpid() + 100_000)
    script_path = tmp_path / "apply-update.ps1"
    script_path.write_text(render_swap_script(plan, windows=True), encoding="utf-8-sig")

    subprocess.run(
        [_POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
        timeout=60,
    )

    log = swap_log_path(script_path)
    assert log.exists(), "hỏng mà không ghi gì lại = lần sau vẫn phải đoán"
    text = log.read_text(encoding="utf-8")
    assert "bắt đầu" in text
    assert "chép bản mới hỏng" in text, "phải ghi ĐÚNG bước hỏng, không chỉ 'có lỗi'"


def test_windows_script_guards_the_working_directory_and_restart() -> None:
    """Ba dòng chống bug khoá thư mục, kiểm ở mức văn bản để đỏ ngay trên máy dev Linux
    (test chạy thật ở trên chỉ chạy được trên Windows)."""
    # So theo SỐ DÒNG LỆNH, không theo vị trí ký tự trong cả file: chuỗi "Move-Item" cũng
    # nằm trong phần chú thích ở đầu script, nên str.index() bắt phải comment chứ không phải
    # lệnh — và test sẽ đỏ vì lý do sai.
    lines = render_swap_script(_windows_plan(), windows=True).splitlines()

    def line_of(command: str) -> int:
        """Số dòng của LỆNH, bỏ qua mọi lần chữ đó xuất hiện trong chú thích."""
        for i, line in enumerate(lines):
            if line.strip().startswith(command):
                return i
        raise AssertionError(f"script không còn lệnh {command}")

    set_location = line_of("Set-Location")
    first_move = line_of("Move-Item")
    assert set_location < first_move, "Set-Location phải đứng TRƯỚC Move-Item, đứng sau thì vô dụng"

    # `Set-Location` MỘT MÌNH không sửa được bug: nó đổi "current location" của provider
    # PowerShell, không đổi thư mục làm việc của tiến trình ở mức Win32 — mà khoá DELETE nằm ở
    # mức Win32. Bản vá đầu chỉ có Set-Location và job check-windows-updater đỏ với
    # returncode 1. Gác riêng dòng này để đừng ai gỡ nó đi lần nữa.
    set_win32_cwd = line_of("[System.IO.Directory]::SetCurrentDirectory")
    assert set_win32_cwd < first_move, (
        "chỉ Set-Location thì Windows vẫn khoá thư mục — phải SetCurrentDirectory ở mức Win32"
    )
    restart = lines[line_of("Start-Process")]
    assert "-WorkingDirectory $installDir" in restart, (
        "thiếu thì launcher mới kế thừa cwd %TEMP% của script"
    )
