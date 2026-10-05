"""Phần chung của mọi cầu nối: chạy việc dài ở luồng nền, báo bận, báo lỗi.

Một giao diện đứng hình vì đang tải 3.629 file là giao diện hỏng, nên KHÔNG có cầu nối nào
được gọi lõi trực tiếp trong slot — tất cả đi qua `run_in_background`.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, QUrl, Signal

from nostalgia.errors import NostalgiaError

# Mọi luồng nền đang sống. Chúng là daemon nên Python tắt không đợi chúng — và một luồng
# đang GỌI QT lúc interpreter tắt thì Qt gỡ mutex dưới chân nó: "mutex lock failure", heap
# hỏng, abort. Người dùng thấy launcher "sập lúc thoát" dù đã làm xong việc.
_live_threads: list[threading.Thread] = []
_live_lock = threading.Lock()


def wait_for_background(timeout: float = 5.0) -> None:
    """Đợi luồng nền xong trước khi thoát. Gọi ở cuối `main()`."""
    with _live_lock:
        threads = list(_live_threads)
    deadline = time.monotonic() + timeout
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))


class WorkerBridge(QObject):
    """QObject biết chạy việc ở luồng nền và giữ cờ `busy` cho QML."""

    busyChanged = Signal()
    activityChanged = Signal()
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._activity = ""
        self._lock = threading.Lock()
        # Thế hệ của yêu cầu mới nhất: kết quả về muộn của yêu cầu cũ bị bỏ, không đè lên mới.
        self._generation = 0

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=activityChanged)
    def activity(self) -> str:
        """Việc đang làm, bằng lời người dùng đọc được — popup góc dưới phải hiện dòng này."""
        return self._activity

    def next_generation(self) -> int:
        with self._lock:
            self._generation += 1
            return self._generation

    def is_current(self, generation: int) -> bool:
        with self._lock:
            return generation == self._generation

    def run_in_background(self, work: Callable[[], None], activity: str = "Đang xử lý...") -> None:
        """Chạy `work` ở luồng nền; lỗi đi ra tín hiệu `failed` thay vì chết lặng."""
        self._activity = activity
        self.activityChanged.emit()

        def guarded() -> None:
            message = ""
            try:
                work()
            except NostalgiaError as error:
                message = str(error)
            except Exception as error:  # biên cuối cùng trước khi lên màn hình
                message = f"lỗi không lường trước: {error}"
            # Cửa sổ có thể đã đóng trong lúc luồng còn chạy; khi đó QObject đã bị huỷ và
            # mọi tín hiệu ném RuntimeError — không còn ai để báo, bỏ qua là đúng.
            with contextlib.suppress(RuntimeError):
                if message:
                    self.failed.emit(message)
                self._set_busy(False)

        def tracked() -> None:
            try:
                guarded()
            finally:
                with _live_lock:
                    _live_threads.remove(thread)

        self._set_busy(True)
        thread = threading.Thread(target=tracked, daemon=True)
        with _live_lock:
            _live_threads.append(thread)
        thread.start()

    def _set_busy(self, busy: bool) -> None:
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit()


def local_path(text: str) -> str:
    """FileDialog/FolderDialog của QML trả URL `file://`; lõi chỉ nhận đường dẫn. Rỗng giữ rỗng."""
    text = text.strip()
    if text.startswith("file:"):
        return QUrl(text).toLocalFile()
    return text
