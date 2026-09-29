"""Hỏng bước nào cũng phải mở lại launcher — miễn thư mục cài còn lành.

Bug "tắt rồi không mở lại" có nguyên nhân gốc là cwd, nhưng cái biến nó thành triệu chứng
là `exit 1` trần: launcher đã thoát trước khi script chạy, nên bất cứ bước nào hỏng mà
script bỏ đi im lặng cũng cho ra đúng cảnh người dùng thấy. Defender giữ file, ổ đầy, thư
mục đang mở trong Explorer — sửa cwd không bịt được mấy cái đó.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from test_update_apply import _POWERSHELL, needs_powershell
from test_update_apply_windows import _windows_plan

from nostalgia.update.apply import SwapPlan, render_swap_script, swap_log_path


@needs_powershell
def test_powershell_reopens_the_launcher_after_a_failed_copy(tmp_path: Path) -> None:
    """Chép hỏng: đã trả lại bản cũ lành lặn rồi thì phải mở nó lên, chứ không `exit 1`
    để người dùng ngồi nhìn màn hình trống.

    Kiểm qua nhật ký chứ không qua tiến trình thật: .exe ở đây là file rỗng nên
    Start-Process hỏng trên mọi hệ, mà điều cần gác là script CÓ GỌI hay không — hỏng vì
    exe giả thì nhánh catch trong Restart ghi lại."""
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

    assert (install / "lib" / "core.dll").read_text(encoding="utf-8") == "cũ"
    text = swap_log_path(script_path).read_text(encoding="utf-8")
    assert "đã trả lại bản cũ" in text
    assert "thử mở lại launcher" in text, "trả lại bản cũ xong phải mở nó lên"


def test_windows_script_does_not_leave_a_bare_exit_with_a_working_install() -> None:
    """Không đường thoát nào được bỏ đi im lặng khi thư mục cài còn lành.

    Đúng hai `exit 1` được phép KHÔNG mở lại: hết hạn chờ PID (launcher cũ vẫn đang chạy, mở
    thêm là hai bản tranh nhau ghi cùng thư mục dữ liệu), và nhánh hỏng-nặng không trả lại
    được bản cũ (không còn gì mà mở). Mọi `exit 1` khác phải có `Restart` đứng trước nó."""
    lines = render_swap_script(_windows_plan(), windows=True).splitlines()
    exits = [i for i, line in enumerate(lines) if line.strip().startswith("exit 1")]
    assert len(exits) == 3, f"số đường thoát đổi ({len(exits)}) — xem lại từng cái một"

    for index in exits:
        before = "\n".join(lines[max(0, index - 6) : index])
        allowed = "hết 60s chờ PID" in before or "HỎNG NẶNG" in before
        assert allowed or "Restart" in before, (
            f"exit 1 ở dòng {index + 1} bỏ đi mà không mở lại launcher:\n{before}"
        )
