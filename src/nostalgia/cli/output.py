"""In ra màn hình. Đây là **module duy nhất** trong kho được phép `print`.

Lõi báo tiến độ qua `on_progress` và diễn giải qua `logging`; việc biến chúng thành chữ trên
terminal là của tầng này. Nhờ ranh giới đó, giao diện đồ hoạ sau này thay đúng file này.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # nạp lười: `doctor` kéo theo cả install/ và zipfile
    from nostalgia.doctor import Diagnosis, Finding
    from nostalgia.operations.progress import Progress


class ProgressPrinter:
    """In tiến độ trên MỘT dòng, chỉ khi phần trăm đổi.

    In mỗi lần gọi sẽ đẩy ra hàng nghìn dòng cho một bản cài 3.500 file, và khi output bị
    chuyển vào file log thì nó nuốt mất mọi thứ khác đáng đọc.
    """

    __slots__ = ("_last_line", "_quiet")

    def __init__(self, *, quiet: bool = False) -> None:
        self._quiet = quiet
        self._last_line = ""

    def __call__(self, progress: Progress) -> None:
        if self._quiet:
            return
        line = f"  {progress.stage}: {progress.done}/{progress.total}"
        if line == self._last_line:
            return
        self._last_line = line
        end = "\n" if progress.done == progress.total else "\r"
        print(f"{line}   ", end=end, flush=True)


def say(message: str) -> None:
    print(message)


def warn(message: str) -> None:
    print(message, file=sys.stderr)


def fail(message: str) -> None:
    print(f"lỗi: {message}", file=sys.stderr)


def print_diagnosis(diagnosis: Diagnosis, version_id: str) -> None:
    """Chặn in ra stderr, cảnh báo in ra stderr, tóm tắt in ra stdout."""
    for finding in diagnosis.fatal_findings:
        warn(f"  ✗ {_describe(finding)}")
    for finding in diagnosis.warnings:
        warn(f"  ! {_describe(finding)}")
    if diagnosis.is_healthy:
        say(
            f"{version_id}: đủ ({diagnosis.checked} mục đã soi, {len(diagnosis.warnings)} cảnh báo)"
        )
    else:
        say(f"{version_id}: thiếu {len(diagnosis.fatal_findings)}/{diagnosis.checked} mục")


def _describe(finding: Finding) -> str:
    return f"{finding.part} {finding.problem}: {finding.path}"
