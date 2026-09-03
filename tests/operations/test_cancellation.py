"""CancelToken — trước đây không có test nào, dù nó sẽ được truyền xuyên qua mọi thao tác dài."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from mccore.errors import Cancelled
from mccore.operations.cancellation import CancelToken


def test_starts_not_cancelled() -> None:
    assert CancelToken().is_cancelled() is False


def test_cancel_is_visible_and_idempotent() -> None:
    cancel_token = CancelToken()
    cancel_token.cancel()
    assert cancel_token.is_cancelled() is True
    cancel_token.cancel()
    assert cancel_token.is_cancelled() is True


def test_raise_if_cancelled_stays_quiet_until_cancelled() -> None:
    cancel_token = CancelToken()
    cancel_token.raise_if_cancelled()  # không được ném gì
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        cancel_token.raise_if_cancelled()


def test_cancellation_is_seen_by_other_threads() -> None:
    """Pool tải có nhiều luồng cùng đọc cờ này, nên nó phải qua được ranh giới luồng."""
    cancel_token = CancelToken()
    seen = threading.Event()

    def worker() -> bool:
        for _ in range(200):
            if cancel_token.is_cancelled():
                seen.set()
                return True
            time.sleep(0.005)
        return False

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        time.sleep(0.02)
        cancel_token.cancel()
        assert future.result(timeout=5) is True
    assert seen.is_set()


def test_many_threads_all_observe_cancellation() -> None:
    """Không luồng nào được treo vĩnh viễn khi cờ đã bật."""
    cancel_token = CancelToken()
    cancel_token.cancel()

    def worker(_index: int) -> bool:
        return cancel_token.is_cancelled()

    with ThreadPoolExecutor(max_workers=16) as pool:
        assert all(pool.map(worker, range(64)))


def test_token_has_no_dict_so_it_cannot_grow_hidden_state() -> None:
    """`__slots__` giữ đối tượng nhỏ và chặn việc gắn thêm trạng thái ngoài ý muốn."""
    cancel_token = CancelToken()
    with pytest.raises(AttributeError):
        cancel_token.trang_thai_la = 1  # type: ignore[attr-defined]
