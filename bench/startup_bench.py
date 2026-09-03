"""Đo độ trễ khởi động CLI và giá phải trả cho từng import nặng.

Không phải test: script in số đo để so với ngân sách trong docs/PERFORMANCE.md.
Không cần mạng.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time

REPEAT = 7
PROBES = (
    ("python trần", "pass"),
    ("import mccore", "import mccore"),
    ("import mccore.cli.main", "import mccore.cli.main"),
    ("import requests", "import requests"),
)


def time_process(code: str) -> float:
    """Đo cả tiến trình con, kể cả thời gian khởi động thông dịch — đúng thứ người dùng chờ."""
    started = time.perf_counter()
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
    return (time.perf_counter() - started) * 1000


def main() -> int:
    print(f"{'phép đo':<28} {'trung vị':>10}")
    for label, code in PROBES:
        samples = [time_process(code) for _ in range(REPEAT)]
        print(f"{label:<28} {statistics.median(samples):8.0f} ms")

    samples = [
        time_process("from mccore.cli.main import main; main(['--version'])") for _ in range(REPEAT)
    ]
    print(f"{'mccore --version (trọn vẹn)':<28} {statistics.median(samples):8.0f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
