"""Thoát launcher phải sạch: mã 0, không hư heap.

Lỗi thật ở v1.1.0: workflow release đổ ở bước "chạy thử gói đóng sẵn" trên CẢ Linux lẫn
Windows, sau khi đã in "smoke ok" — tức là việc làm xong rồi mới sập lúc thoát. Luồng nền
dựng icon khối là daemon, nên Python tắt không đợi nó; nó còn đang gọi Qt thì Qt gỡ mutex
dưới chân nó ("mutex lock failure"), heap hỏng, abort mã 134.

Test chạy TIẾN TRÌNH CON thật chứ không gọi hàm: hư heap chỉ lộ ra ở mã thoát của tiến
trình, trong cùng tiến trình pytest thì không thấy gì.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

SRC = Path(__file__).resolve().parents[2] / "src"


def test_the_launcher_exits_without_corrupting_the_heap(tmp_path: Path) -> None:
    environment = dict(os.environ)
    environment.update(
        NOSTALGIA_SMOKE_TEST="1",
        QT_QPA_PLATFORM="offscreen",
        HOME=str(tmp_path / "home"),
        XDG_CONFIG_HOME=str(tmp_path / "home" / ".config"),
        XDG_DATA_HOME=str(tmp_path / "home" / ".local" / "share"),
        PYTHONPATH=str(SRC),
    )
    (tmp_path / "home").mkdir()

    done = subprocess.run(
        [sys.executable, "-c", "from nostalgia.ui.app import main; raise SystemExit(main([]))"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert "smoke ok" in done.stdout, f"cửa sổ không dựng được: {done.stderr[-800:]}"
    assert done.returncode == 0, (
        f"thoát mã {done.returncode} (134 = abort vì hư heap): {done.stderr[-800:]}"
    )
    for noise in ("mutex lock failure", "malloc", "terminate called"):
        assert noise not in done.stderr, f"thoát bẩn: {done.stderr[-800:]}"
