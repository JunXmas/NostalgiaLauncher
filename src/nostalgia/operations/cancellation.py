"""Yêu cầu dừng, truyền xuyên qua mọi thao tác dài.

Lõi không tự sinh thread nào ngoài pool tải, nên việc chạy nền là chuyện của người gọi;
thứ lõi cần là một cách để biết "thôi, dừng đi" mà không phụ thuộc vào giao diện nào.
"""

from __future__ import annotations

import threading

from nostalgia.errors import Cancelled


class CancelToken:
    """Cờ dừng an toàn giữa các luồng.

    Dùng `threading.Event` chứ không phải một biến `bool`: pool tải có nhiều luồng cùng đọc,
    và `Event` cho phép luồng khác đợi mà không quay vòng bận.
    """

    __slots__ = ("_event",)

    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        """Ném `Cancelled` nếu đã bị yêu cầu dừng. Gọi ở đầu mỗi việc con."""
        if self._event.is_set():
            raise Cancelled
