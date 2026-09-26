"""Áp bản mới đã bung: chỉ làm được khi launcher chạy từ gói đóng sẵn (PyInstaller, `sys.frozen`).

Không thể tự ghi đè chính mình trong lúc đang chạy (Windows khoá file, Linux thì file đang
mở), nên launcher viết một script tráo thư mục rồi thoát; script chờ tiến trình cũ tắt, đổi
`install` → `install.old`, chép bản mới vào, xoá bản cũ, mở launcher mới. Chép hỏng thì trả
lại thư mục cũ — người dùng không bao giờ bị mất launcher.

Trên Windows script là POWERSHELL, không phải batch. Bản batch (đến 1.1.0) chết ba đường
cùng lúc, và vì nó chạy sau khi launcher đã thoát nên chết hoàn toàn im lặng:
  • `timeout /t` thoát ngay khi stdin bị redirect (launcher spawn `cmd.exe` với
    stdin=DEVNULL) — vòng chờ không ngủ giây nào, quay hết 600 lượt rồi bỏ cuộc;
  • batch ghi UTF-8 nhưng `cmd.exe` đọc theo OEM codepage — tên người dùng Windows có dấu
    tiếng Việt là mọi đường dẫn trong script thành rác;
  • `move` không thử lại khi Defender còn giữ file exe một nhịp sau khi tiến trình thoát.
PowerShell 5.1 có sẵn trên mọi Windows 10/11, đọc UTF-8 có BOM đúng, `Wait-Process` chờ
PID tử tế, `Start-Sleep` không đụng stdin.

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
from nostalgia.system.platform_info import CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW

INSTALL_KIND_FROZEN = "frozen"
INSTALL_KIND_SOURCE = "source"
INSTALL_KIND_APP = "app"
# AppImage: mount squashfs chỉ-đọc (`/tmp/.mount_*`) — biến môi trường `APPIMAGE`
# do runtime AppImage tự đặt, không cần đụng tới install_dir để biết.
INSTALL_KIND_APPIMAGE = "appimage"
# Không có quyền ghi vào install_dir: gói .deb/.rpm cài ở /opt (chủ là root), hoặc Windows
# cài toàn máy vào Program Files (cần admin). Cùng một nguyên nhân gốc nên gộp một kiểu.
INSTALL_KIND_READONLY = "readonly"
EXECUTABLE_NAME = "nostalgia-ui"

# Câu tiếng Việt cho từng kiểu không tráo được — dùng khi báo lỗi thay cho exception thô.
_BLOCKED_REASONS: dict[str, str] = {
    INSTALL_KIND_SOURCE: "đang chạy từ mã nguồn: cập nhật bằng `git pull` và `uv sync`",
    INSTALL_KIND_APPIMAGE: (
        "bạn đang chạy bản AppImage (gắn kết chỉ-đọc, không tự tráo được): "
        "tải bản AppImage mới ở trang release rồi thay file .AppImage cũ"
    ),
    INSTALL_KIND_READONLY: (
        "thư mục cài không có quyền ghi (cài bằng .deb/.rpm, hoặc cần quyền quản trị): "
        "tải bản mới ở trang release rồi cài đè bằng đúng cách bạn đã cài lần đầu"
    ),
}


def blocked_install_reason(install_kind: str) -> str:
    """Câu tiếng Việt giải thích vì sao `install_kind` không tự áp bản mới tại chỗ được.

    Trả về câu mặc định (kiểu chạy từ mã nguồn) cho kiểu chưa có câu riêng — chỉ `frozen`
    mới thực sự tráo được nên không cần câu ở đây."""
    return _BLOCKED_REASONS.get(install_kind, _BLOCKED_REASONS[INSTALL_KIND_SOURCE])


def clean_child_env() -> dict[str, str]:
    """Trả về bản sao ``os.environ`` đã gỡ ``LD_LIBRARY_PATH`` (và
    ``DYLD_LIBRARY_PATH``) mà PyInstaller ghi đè.

    PyInstaller lưu giá trị gốc vào biến ``*_ORIG``; nếu biến đó tồn tại ta
    khôi phục, ngược lại xoá hẳn — tránh launcher mới kế thừa đường dẫn trỏ
    vào thư mục bản cũ (đã bị xoá sau swap).
    """
    env = os.environ.copy()
    for var in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        original = env.pop(var + "_ORIG", None)
        if original is not None:
            env[var] = original
        else:
            env.pop(var, None)
    return env


@dataclass(frozen=True, slots=True)
class SwapPlan:
    """Mọi thứ script tráo cần biết. Thuần dữ liệu để test không phải chạy script thật."""

    install_dir: Path
    staged_dir: Path
    executable: Path
    wait_pid: int


def detect_install_kind() -> str:
    """`frozen`: gói onedir tự tráo được. `app`: gói macOS .app — thư mục thực thi nằm trong
    Contents/, tráo kiểu onedir sẽ làm hỏng bundle nên chỉ mở trang tải. `source`: mã nguồn.
    `appimage`: biến môi trường `APPIMAGE` báo runtime đang chạy từ mount squashfs chỉ-đọc —
    tráo vào đó vô nghĩa. `readonly`: `install_dir` tồn tại nhưng không ghi được (`.deb`/`.rpm`
    ở `/opt` chủ root, hoặc cài toàn máy trên Windows cần admin)."""
    if not getattr(sys, "frozen", False):
        return INSTALL_KIND_SOURCE
    if sys.platform == "darwin":
        return INSTALL_KIND_APP
    if os.environ.get("APPIMAGE"):
        return INSTALL_KIND_APPIMAGE
    if not _dir_is_writable(current_install_dir()):
        return INSTALL_KIND_READONLY
    return INSTALL_KIND_FROZEN


def _dir_is_writable(directory: Path) -> bool:
    """Thử ghi THẬT một file tạm rồi xoá. `os.access(..., os.W_OK)` trên Windows chỉ nhìn
    thuộc tính read-only chứ không nhìn ACL — cài toàn máy vào Program Files nó vẫn báo
    "ghi được", rồi script tráo chết im lặng ở bước move."""
    probe = directory / f".nostalgia-write-probe-{os.getpid()}"
    try:
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False


def current_install_dir() -> Path:
    """Thư mục chứa launcher đang chạy (gói onedir của PyInstaller)."""
    return Path(sys.executable).resolve().parent


def render_swap_script(plan: SwapPlan, *, windows: bool = os.name == "nt") -> str:
    """Nội dung script tráo thư mục cho hệ đang chạy."""
    if windows:
        return _render_ps1(plan)
    return _render_sh(plan)


def write_swap_script(
    plan: SwapPlan, scripts_dir: Path, *, windows: bool = os.name == "nt"
) -> Path:
    ensure_dir(scripts_dir)
    script_path = scripts_dir / ("apply-update.ps1" if windows else "apply-update.sh")
    # utf-8-sig: PowerShell 5.1 đọc file KHÔNG BOM theo ANSI codepage — đường dẫn có dấu
    # tiếng Việt (C:\Users\Tuấn\...) thành rác. BOM là cách duy nhất ép nó đọc UTF-8.
    script_path.write_text(
        render_swap_script(plan, windows=windows),
        encoding="utf-8-sig" if windows else "utf-8",
    )
    if not windows:
        set_executable(script_path)
    return script_path


def launch_swap_script(script_path: Path, *, windows: bool = os.name == "nt") -> None:
    """Chạy script tách hẳn khỏi launcher, để launcher thoát mà script vẫn sống."""
    if windows:
        # DETACHED_PROCESS (bỏ ở đây) chỉ nói "đừng kế thừa console của cha" — tiến trình vẫn
        # tự AllocConsole và Windows dựng một cửa sổ mới. CREATE_NO_WINDOW mới là cờ đúng,
        # nhưng nó bị Windows lờ đi khi dùng chung DETACHED_PROCESS, nên phải THAY chứ không
        # phải thêm. Bỏ DETACHED_PROCESS không làm script chết theo cha: Windows không có
        # process-tree kill mặc định, và không có JobObject nào ràng script vào launcher.
        #
        # `powershell.exe` (5.1) chứ không `cmd.exe`: xem docstring đầu file — batch chết
        # ở stdin=DEVNULL (timeout /t), ở codepage (đường dẫn có dấu), và không retry được.
        subprocess.Popen(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            creationflags=CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    # start_new_session=True gọi setsid() trước fork — an toàn hơn preexec_fn vì Python xử lý
    # trước khi exec, không bao giờ ném "Operation not permitted" (preexec_fn ném lỗi này
    # khi launcher đã là session leader, ví dụ chạy từ terminal hoặc .desktop file).
    subprocess.Popen(
        ["/bin/sh", str(script_path)],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        env=clean_child_env(),
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
nohup {executable} </dev/null >/dev/null 2>&1 &
"""


def _render_ps1(plan: SwapPlan) -> str:
    install, staged = _quote_ps(plan.install_dir), _quote_ps(plan.staged_dir)
    old = _quote_ps(plan.install_dir.with_name(plan.install_dir.name + ".old"))
    executable = _quote_ps(plan.executable)
    # KHÔNG dùng `$PID` làm tên biến chờ — đó là biến tự động của PowerShell (PID của chính
    # script). `Move-Item` có vòng thử lại vì Defender hay giữ file exe thêm vài giây sau
    # khi tiến trình đã thoát — đúng lúc script này chạy.
    return f"""# Nostalgia Launcher — tráo bản mới sau khi launcher cũ thoát. Tự sinh, đừng sửa tay.
$ErrorActionPreference = 'Stop'
$installDir = {install}
$stagedDir = {staged}
$oldDir = {old}
$exePath = {executable}

$deadline = (Get-Date).AddSeconds(60)
while (Get-Process -Id {plan.wait_pid} -ErrorAction SilentlyContinue) {{
    if ((Get-Date) -gt $deadline) {{ exit 1 }}
    Start-Sleep -Milliseconds 200
}}

if (Test-Path -LiteralPath $oldDir) {{
    Remove-Item -LiteralPath $oldDir -Recurse -Force
}}
$moved = $false
for ($try = 0; $try -lt 30; $try++) {{
    try {{
        Move-Item -LiteralPath $installDir -Destination $oldDir -Force
        $moved = $true
        break
    }} catch {{
        Start-Sleep -Seconds 1
    }}
}}
if (-not $moved) {{ exit 1 }}

try {{
    Copy-Item -LiteralPath $stagedDir -Destination $installDir -Recurse -Force
}} catch {{
    Remove-Item -LiteralPath $installDir -Recurse -Force -ErrorAction SilentlyContinue
    Move-Item -LiteralPath $oldDir -Destination $installDir -Force
    exit 1
}}
Remove-Item -LiteralPath $oldDir -Recurse -Force -ErrorAction SilentlyContinue
Start-Process -FilePath $exePath
"""


def _quote(path: Path) -> str:
    return "'" + str(path).replace("'", "'\\''") + "'"


def _quote_ps(path: Path) -> str:
    """Chuỗi đơn của PowerShell: chỉ cần nhân đôi dấu nháy đơn, không nội suy gì khác."""
    return "'" + str(path).replace("'", "''") + "'"
