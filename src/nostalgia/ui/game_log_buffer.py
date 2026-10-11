"""Giới hạn nhật ký trong RAM ngay cả khi luồng giao diện chưa kịp gom lô."""

from __future__ import annotations

from collections import deque

MAX_LINES = 5000
MAX_LOG_CHARACTERS = 1024 * 1024
MAX_LINE_CHARACTERS = 8192


class LogBuffer:
    """Giữ đuôi log theo cả số dòng và số ký tự; không sửa log trên đĩa."""

    def __init__(self) -> None:
        self._lines: deque[str] = deque()
        self._characters = 0

    def append(self, line: str) -> str:
        """Giữ đầu và cuối dòng quá dài, rồi bỏ dòng cũ khi vượt ngân sách."""
        if len(line) > MAX_LINE_CHARACTERS:
            marker = " … "
            head = MAX_LINE_CHARACTERS // 2
            tail = MAX_LINE_CHARACTERS - head - len(marker)
            line = line[:head] + marker + line[-tail:]
        self._lines.append(line)
        self._characters += len(line)
        while len(self._lines) > MAX_LINES or self._characters > MAX_LOG_CHARACTERS:
            self._characters -= len(self._lines.popleft())
        return line

    def clear(self) -> None:
        self._lines.clear()
        self._characters = 0

    def take(self) -> list[str]:
        """Chuyển phần đuôi đang giữ cho luồng giao diện và bắt đầu lô mới."""
        lines = list(self._lines)
        self.clear()
        return lines
