"""Sinh nội dung script tráo thư mục — phần chữ, tách khỏi phần chạy ở `apply.py`.

Script chạy SAU khi launcher thoát, stdout/stderr đổ vào DEVNULL — hỏng là hỏng câm. Đó là
lý do bug "tắt rồi không mở lại" trên Windows sống qua nhiều bản: mỗi lần sửa đều là đoán từ
triệu chứng. Bản PowerShell vì thế ghi nhật ký cạnh chính nó và mở lại launcher ở mọi đường
thoát mà thư mục cài còn lành. Xem chú thích trong từng script cho từng quyết định.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Chỉ để chú thích kiểu. Import thật sẽ vòng: apply.py import hai hàm render ở đây.
    from nostalgia.update.apply import SwapPlan


def render_sh(plan: SwapPlan) -> str:
    install, staged = _quote(plan.install_dir), _quote(plan.staged_dir)
    old = _quote(str(plan.install_dir) + ".old")
    executable = _quote(plan.executable)
    # Script sh KHÔNG có nhật ký và KHÔNG mở lại launcher ở đường hỏng, khác bản PowerShell.
    # Cố ý: jun xác nhận tự cập nhật trên Linux chạy đúng, và mỗi dòng thêm vào một đường đang
    # chạy được là một chỗ có thể làm nó hỏng. Bản Windows cần vì nó hỏng thật, có người báo.
    # ponytail: đường hỏng ở đây vẫn im lặng — thêm log + mở lại như bản ps1 khi nào có người
    # dùng Linux báo "bấm cập nhật rồi app không mở lại", không phải trước đó.
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


def render_ps1(plan: SwapPlan) -> str:
    install, staged = _quote_ps(plan.install_dir), _quote_ps(plan.staged_dir)
    old = _quote_ps(str(plan.install_dir) + ".old")
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
# Nhật ký nằm cạnh chính script này ($PSCommandPath), không phải một đường dẫn truyền vào:
# script luôn biết nó ở đâu, nên không có tham số nào để truyền sai. Xem swap_log_path().
$logPath = [System.IO.Path]::ChangeExtension($PSCommandPath, '.log')

# Ghi nhật ký: script này chạy sau khi launcher thoát, stdout/stderr đều DEVNULL. Không có
# file này thì hỏng là hỏng câm, và lần sau lại phải đoán từ triệu chứng.
function Log($m) {{
    try {{
        Add-Content -LiteralPath $logPath -Value "$(Get-Date -Format o) $m" -Encoding utf8
    }} catch {{ }}
}}
Log "bắt đầu; cwd=$([System.IO.Directory]::GetCurrentDirectory()); install=$installDir"

# Đứng ra chỗ trung lập TRƯỚC KHI đụng vào thư mục cài. Windows giữ handle không cho DELETE
# trên thư mục làm việc của tiến trình đang sống, nên nếu cwd nằm trong (hay LÀ) thư mục cài
# thì Move-Item bên dưới ném "Access denied" mãi mãi — script tự khoá thứ nó định dời.
# Launcher đã truyền cwd=%TEMP% khi spawn; hai dòng này là tầng phòng thủ thứ hai, cho cả
# trường hợp ai đó chạy tay script từ trong thư mục cài.
#
# PHẢI gọi [System.IO.Directory]::SetCurrentDirectory. `Set-Location` MỘT MÌNH KHÔNG ĐỦ: nó
# chỉ đổi "current location" của PowerShell provider (thứ $PWD trả về) chứ không đổi thư mục
# làm việc thật của tiến trình ở mức Win32 — mà cái khoá DELETE nằm đúng ở mức Win32 đó.
# Job check-windows-updater trên Windows thật đã bắt được: chỉ Set-Location thì Move-Item vẫn
# "Access denied", test đỏ với returncode 1. Giữ cả hai dòng vì Set-Location là thứ mọi lệnh
# PowerShell tương đối dùng, còn SetCurrentDirectory là thứ Windows thực sự nhìn.
Set-Location -LiteralPath ([System.IO.Path]::GetTempPath())
[System.IO.Directory]::SetCurrentDirectory([System.IO.Path]::GetTempPath())
Log "đã ra chỗ trung lập; cwd=$([System.IO.Directory]::GetCurrentDirectory())"

# Mở lại launcher. Gọi ở MỌI đường thoát mà thư mục cài đang lành — kể cả đường hỏng.
#
# Đây là bài học đắt nhất của bug "tắt rồi không mở lại": nguyên nhân gốc là cwd, nhưng cái
# biến nó thành triệu chứng ấy là `exit 1` trần. Launcher đã thoát từ trước, nên bất cứ bước
# nào hỏng mà script bỏ đi im lặng cũng cho ra đúng cảnh người dùng thấy. Và còn vô số cách
# để move hỏng ngoài cwd: Defender giữ file, phần mềm diệt virus khác, ổ đầy, thư mục đang mở
# trong Explorer. Sửa riêng cwd chỉ bịt một lối vào cùng một cái hố.
#
# -WorkingDirectory: không đặt thì launcher mới kế thừa cwd của script, mà ta vừa chuyển sang
# %TEMP% — app sẽ chạy với thư mục làm việc trỏ vào thư mục tạm, rồi lần cập nhật SAU lại
# spawn script từ đó. Đặt thẳng thư mục cài cho đúng như lúc người dùng bấm lối tắt.
function Restart($why) {{
    Log "thử mở lại launcher ($why)"
    try {{
        Start-Process -FilePath $exePath -WorkingDirectory $installDir
        Log "đã mở lại launcher"
    }} catch {{
        Log "KHÔNG mở lại được: $($_.Exception.Message)"
    }}
}}

$deadline = (Get-Date).AddSeconds(60)
while (Get-Process -Id {plan.wait_pid} -ErrorAction SilentlyContinue) {{
    if ((Get-Date) -gt $deadline) {{
        # Launcher cũ không chịu thoát. KHÔNG mở lại: sẽ có hai bản chạy cùng lúc, tranh nhau
        # ghi cùng một thư mục dữ liệu. Thoát im là đúng ở đây — app người dùng vẫn đang mở.
        Log "hết 60s chờ PID {plan.wait_pid} thoát; không tráo, không mở thêm bản thứ hai"
        exit 1
    }}
    Start-Sleep -Milliseconds 200
}}

if (Test-Path -LiteralPath $oldDir) {{
    Remove-Item -LiteralPath $oldDir -Recurse -Force
}}
$moved = $false
$lastError = ''
for ($try = 0; $try -lt 30; $try++) {{
    try {{
        Move-Item -LiteralPath $installDir -Destination $oldDir -Force
        $moved = $true
        break
    }} catch {{
        $lastError = $_.Exception.Message
        Start-Sleep -Seconds 1
    }}
}}
if (-not $moved) {{
    # Thư mục cài chưa bị đụng tới, nên bản cũ vẫn chạy được. Mở nó lên: người dùng mất bản
    # cập nhật, nhưng KHÔNG mất launcher — và thấy ngay app còn sống thay vì tưởng nó chết.
    Log "không dời được thư mục cài sau 30 lần: $lastError"
    Restart "không dời được, bản cũ còn nguyên"
    exit 1
}}

try {{
    Copy-Item -LiteralPath $stagedDir -Destination $installDir -Recurse -Force
}} catch {{
    Log "chép bản mới hỏng, trả lại bản cũ: $($_.Exception.Message)"
    Remove-Item -LiteralPath $installDir -Recurse -Force -ErrorAction SilentlyContinue
    try {{
        Move-Item -LiteralPath $oldDir -Destination $installDir -Force
        Log "đã trả lại bản cũ"
        Restart "chép hỏng, đã trả lại bản cũ"
    }} catch {{
        # Đường tệ nhất: bản mới chép hỏng MÀ bản cũ cũng không trả lại được. Không mở lại
        # được gì, nhưng phải ghi rõ để người dùng gửi nhật ký còn biết thư mục .old nằm đâu
        # mà cứu bằng tay — đừng bỏ đi im lặng.
        Log "HỎNG NẶNG: không trả lại được bản cũ, nó nằm ở $oldDir."
        Log "Cách cứu: đổi tên $oldDir thành $installDir. Lỗi: $($_.Exception.Message)"
    }}
    exit 1
}}
Remove-Item -LiteralPath $oldDir -Recurse -Force -ErrorAction SilentlyContinue

Restart "tráo xong"
"""


def _quote(path: object) -> str:
    return "'" + str(path).replace("'", "'\\''") + "'"


def _quote_ps(path: object) -> str:
    """Chuỗi đơn của PowerShell: chỉ cần nhân đôi dấu nháy đơn, không nội suy gì khác."""
    return "'" + str(path).replace("'", "''") + "'"
