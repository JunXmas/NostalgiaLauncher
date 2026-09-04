"""Đo độ trễ khởi động CLI, tính theo BỘI SỐ của thời gian khởi động Python trần.

Vì sao không dùng mili-giây tuyệt đối: trên máy có bộ điều tần CPU, cùng một phép đo cho
34 ms khi máy rảnh và 22 ms khi máy đang bận (xung nhịp được boost) — dao động tới 3 lần,
ngược chiều trực giác. Bội số so với Python trần thì ổn định (1,75-1,80 qua các trạng thái
đó), nên ngân sách phải đặt theo bội số.

Các phép đo được chạy XEN KẼ chứ không tuần tự, để mọi probe cùng chịu một trạng thái xung
nhịp. Không phải test: script in số đo để so với docs/PERFORMANCE.md. Không cần mạng.
"""

from __future__ import annotations

import os
import statistics
import subprocess
import sys
import time

REPEAT = 15
BASELINE = "pass"
PROBES = {
    "python trần": BASELINE,
    "import mccore": "import mccore",
    "import mccore.cli.main": "import mccore.cli.main",
    "mccore --version (trọn vẹn)": "from mccore.cli.main import main; main(['--version'])",
    "+ http.client": "import mccore.cli.main, http.client",
    "+ logging": "import mccore.cli.main, logging",
    "+ zipfile": "import mccore.cli.main, zipfile",
    "+ concurrent.futures": "import mccore.cli.main, concurrent.futures",
    "+ subprocess": "import mccore.cli.main, subprocess",
    "+ tất cả thứ nặng": (
        "import mccore.cli.main, http.client, logging, zipfile, concurrent.futures, subprocess"
    ),
}


def time_process(code: str) -> float:
    """Đo cả tiến trình con, kể cả khởi động thông dịch — đúng thứ người dùng phải chờ."""
    started = time.perf_counter()
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
    return (time.perf_counter() - started) * 1000


def main() -> int:
    samples: dict[str, list[float]] = {probe_name: [] for probe_name in PROBES}
    for _ in range(REPEAT):  # xen kẽ: một lượt chạy hết mọi probe rồi mới lặp
        for probe_name, code in PROBES.items():
            samples[probe_name].append(time_process(code))

    medians = {probe_name: statistics.median(values) for probe_name, values in samples.items()}
    baseline = medians["python trần"]
    print(f"tải hệ thống lúc đo: {os.getloadavg()[0]:.2f}")
    print(f"{'phép đo':<30} {'trung vị':>10} {'bội số nền':>12}")
    for probe_name in PROBES:
        median = medians[probe_name]
        print(f"{probe_name:<30} {median:8.1f} ms {median / baseline:11.2f}x")
    print("\nsố tuyệt đối phụ thuộc xung nhịp CPU; chỉ bội số mới so sánh được giữa các lần đo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
