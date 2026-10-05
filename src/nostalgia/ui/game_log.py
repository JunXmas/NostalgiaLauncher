"""Nhật ký game thời gian thực cho giao diện, và câu tóm tắt vì sao game thoát.

Luồng đọc output của game gọi `receive(line)` hàng trăm lần mỗi giây khi mod nạp; đẩy từng
dòng qua tín hiệu Qt là hàng trăm sự kiện/giây lên luồng giao diện. Thay vào đó: dòng vào
bộ đệm có khoá, một `QTimer` 100 ms ở luồng giao diện gom cả lô rồi nối vào model một lần.
Model giữ tối đa `MAX_LINES` dòng — game chạy cả buổi không được làm launcher phình RAM.
"""

from __future__ import annotations

import threading
from collections import deque

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication

GAME_LOG_TAIL_LINES = 60
CRASH_MARKER = "Crash report saved to:"
MAX_LINES = 5000
DRAIN_INTERVAL_MS = 100

TEXT_ROLE = Qt.ItemDataRole.UserRole + 1
LEVEL_ROLE = Qt.ItemDataRole.UserRole + 2

LEVEL_MARKERS = (("/FATAL]", "error"), ("/ERROR]", "error"), ("/WARN]", "warn"))


def classify_level(line: str) -> str:
    """Cấp độ của một dòng log Minecraft: `[12:00:00] [Render thread/WARN]: ...` → warn.
    Dòng stack trace (thụt đầu dòng `at ...`, `Caused by`) và ngoại lệ Java tính là error."""
    for marker, level in LEVEL_MARKERS:
        if marker in line:
            return level
    stripped = line.lstrip()
    if stripped.startswith(("at ", "Caused by:", "... ")) or "Exception" in line:
        return "error"
    return "info"


def describe_game_failure(exit_code: int, tail: list[str]) -> str:
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


class GameLogModel(QAbstractListModel):
    """Danh sách dòng log cho ListView: vai `text` và `level` (info/warn/error)."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lines: list[tuple[str, str]] = []

    def rowCount(self, _parent: QModelIndex | QPersistentModelIndex | None = None) -> int:
        return len(self._lines)

    def roleNames(self) -> dict[int, QByteArray]:
        return {TEXT_ROLE: QByteArray(b"text"), LEVEL_ROLE: QByteArray(b"level")}

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = TEXT_ROLE) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._lines):
            return None
        text, level = self._lines[index.row()]
        return text if role == TEXT_ROLE else level

    @property
    def lines(self) -> list[str]:
        return [text for text, _level in self._lines]

    def append_lines(self, lines: list[str]) -> None:
        if not lines:
            return
        first = len(self._lines)
        self.beginInsertRows(QModelIndex(), first, first + len(lines) - 1)
        self._lines.extend((line, classify_level(line)) for line in lines)
        self.endInsertRows()
        overflow = len(self._lines) - MAX_LINES
        if overflow > 0:
            self.beginRemoveRows(QModelIndex(), 0, overflow - 1)
            del self._lines[:overflow]
            self.endRemoveRows()

    def clear(self) -> None:
        if not self._lines:
            return
        self.beginResetModel()
        self._lines.clear()
        self.endResetModel()


class GameLogFeed(QObject):
    """Cầu giữa luồng đọc output của game và model trên luồng giao diện."""

    lineCountChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model = GameLogModel(self)
        self._pending: list[str] = []
        self._tail: deque[str] = deque(maxlen=GAME_LOG_TAIL_LINES)
        self._lock = threading.Lock()
        self._drain_timer = QTimer(self)
        self._drain_timer.setInterval(DRAIN_INTERVAL_MS)
        self._drain_timer.timeout.connect(self.drain)

    @property
    def model(self) -> GameLogModel:
        return self._model

    @Property(QObject, constant=True)
    def logModel(self) -> GameLogModel:
        """Cùng model, dưới dạng thuộc tính Qt để QML gán vào ListView."""
        return self._model

    @property
    def tail(self) -> deque[str]:
        """Đuôi log gần nhất, đọc được từ luồng nền (dùng cho câu báo lỗi)."""
        return self._tail

    @property
    def tail_snapshot(self) -> list[str]:
        """Bản chụp an toàn giữa các luồng của đuôi log, dùng khi game thoát."""
        with self._lock:
            return list(self._tail)

    def reset(self) -> None:
        """Game sắp chạy: bỏ phần đệm của lần trước. Gọi được từ luồng nền, NGAY trước khi
        chạy game — để những dòng đầu tiên không bị xoá oan khi `begin_session` tới muộn."""
        with self._lock:
            self._pending.clear()
            self._tail.clear()

    def begin_session(self) -> None:
        """Game đã chạy: xoá nhật ký cũ trên màn hình, bắt đầu gom lô. Gọi từ luồng giao diện.
        Không đụng bộ đệm: dòng nhận trước lúc này vẫn còn nguyên để gom ở nhịp đầu."""
        self._model.clear()
        self.lineCountChanged.emit()
        self._drain_timer.start()

    def end_session(self) -> None:
        """Game đã thoát: gom nốt phần còn lại rồi dừng timer. Gọi từ luồng giao diện."""
        self._drain_timer.stop()
        self.drain()

    def receive(self, line: str) -> None:
        """Nhận một dòng từ LUỒNG BẤT KỲ. Rẻ: chỉ nối vào bộ đệm."""
        with self._lock:
            self._pending.append(line)
            self._tail.append(line)

    @Slot()
    def drain(self) -> None:
        with self._lock:
            batch, self._pending = self._pending, []
        if batch:
            self._model.append_lines(batch)
            self.lineCountChanged.emit()

    @Slot(result=str)
    def allText(self) -> str:
        return "\n".join(self._model.lines)

    @Slot()
    def copyAll(self) -> None:
        """Sao chép toàn bộ nhật ký vào clipboard để dán vào báo lỗi."""
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.allText())
