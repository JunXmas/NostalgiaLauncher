"""Phần chung của mọi cầu nối: chạy việc dài ở luồng nền, báo bận, báo lỗi.

Một giao diện đứng hình vì đang tải 3.629 file là giao diện hỏng, nên KHÔNG có cầu nối nào
được gọi lõi trực tiếp trong slot — tất cả đi qua `run_in_background`.
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable

from PySide6.QtCore import Property, QObject, Signal

from nostalgia.errors import NostalgiaError


class WorkerBridge(QObject):
    """QObject biết chạy việc ở luồng nền và giữ cờ `busy` cho QML."""

    busyChanged = Signal()
    failed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._lock = threading.Lock()
        # Thế hệ của yêu cầu mới nhất: kết quả về muộn của yêu cầu cũ bị bỏ, không đè lên mới.
        self._generation = 0

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    def next_generation(self) -> int:
        with self._lock:
            self._generation += 1
            return self._generation

    def is_current(self, generation: int) -> bool:
        with self._lock:
            return generation == self._generation

    def run_in_background(self, work: Callable[[], None]) -> None:
        """Chạy `work` ở luồng nền; lỗi đi ra tín hiệu `failed` thay vì chết lặng."""

        def guarded() -> None:
            try:
                work()
            except NostalgiaError as error:
                self.failed.emit(str(error))
            except RuntimeError:
                # Cửa sổ đã đóng, QObject bị huỷ trong lúc luồng còn chạy: không còn ai để báo.
                return
            except Exception as error:
                self.failed.emit(f"lỗi không lường trước: {error}")
            finally:
                with contextlib.suppress(RuntimeError):
                    self._set_busy(False)

        self._set_busy(True)
        threading.Thread(target=guarded, daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        if self._busy != busy:
            self._busy = busy
            self.busyChanged.emit()
