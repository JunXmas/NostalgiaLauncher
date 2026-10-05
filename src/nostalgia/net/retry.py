"""Thử lại có lùi dần (backoff) cho một việc chạm mạng.

Tách khỏi `http.py` để mỗi file ngắn; `HttpClient` không tự thử lại — một lần gọi là MỘT lần
thử, vì chỉ người gọi biết cách bỏ đi phần đã ghi dở.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from nostalgia.errors import Cancelled, IntegrityError, NetworkError
from nostalgia.operations.cancellation import CancelToken


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Thử lại bao nhiêu lần, chờ bao lâu, và tổng cộng không quá bao lâu.

    `total_deadline_seconds` là thứ `timeout` của socket KHÔNG cho: timeout chỉ áp cho mỗi
    lần đọc, nên một máy chủ nhỏ giọt một byte mỗi 29 giây sẽ treo vô hạn mà không lần đọc
    nào quá hạn.
    """

    attempts: int = 4
    initial_backoff_seconds: float = 0.5
    backoff_multiplier: float = 2.0
    total_deadline_seconds: float = 300.0


DEFAULT_RETRY_POLICY = RetryPolicy()


def retry[T](
    operation: Callable[[], T],
    *,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
    cancel_token: CancelToken | None = None,
) -> T:
    """Chạy lại `operation` theo backoff nhân đôi, cho tới khi xong hoặc hết hạn.

    Chỉ thử lại `NetworkError` và `IntegrityError`: tải dở dang và file hỏng đều là tình
    huống nhất thời trên CDN. Mọi lỗi khác nổi lên ngay — thử lại một lỗi lập trình chỉ làm
    chậm việc phát hiện nó.
    """
    deadline = time.monotonic() + policy.total_deadline_seconds
    backoff = policy.initial_backoff_seconds
    last_error: Exception | None = None

    for attempt in range(1, policy.attempts + 1):
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        try:
            return operation()
        except (NetworkError, IntegrityError) as exc:
            last_error = exc
            remaining = deadline - time.monotonic()
            if attempt == policy.attempts or remaining <= 0:
                break
            if cancel_token is not None and cancel_token.is_cancelled():
                raise Cancelled from exc
            time.sleep(min(backoff, remaining))
            backoff *= policy.backoff_multiplier

    message = f"thất bại sau {policy.attempts} lần thử: {last_error}"
    raise NetworkError(message) from last_error
