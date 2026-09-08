"""Đọc đuôi log của game để nói được VÌ SAO nó thoát, thay vì im lặng về "Sẵn sàng"."""

from __future__ import annotations

from collections import deque

GAME_LOG_TAIL_LINES = 60
CRASH_MARKER = "Crash report saved to:"


def describe_game_failure(exit_code: int, tail: deque[str]) -> str:
    """Một câu cho dải đỏ: mã thoát, và dòng có ích nhất trong đuôi log (báo cáo crash nếu
    có, không thì lỗi Java cuối cùng)."""
    lines = [line.strip() for line in tail if line.strip()]
    crash = next((line for line in reversed(lines) if CRASH_MARKER in line), "")
    if crash:
        return f"Game thoát (mã {exit_code}). {crash.split(CRASH_MARKER, 1)[1].strip(' #@!')}"
    error = next((line for line in reversed(lines) if "Exception" in line or "Error" in line), "")
    return f"Game thoát (mã {exit_code}). " + (
        error[:160] if error else "Xem log trong thư mục bản chơi."
    )
