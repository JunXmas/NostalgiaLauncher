"""Progress: tỉ lệ luôn nằm trong 0..1, kể cả với đầu vào vô lý."""

from __future__ import annotations

import pytest

from mccore.operations.progress import Progress, ignore_progress


@pytest.mark.parametrize(
    ("done", "total", "expected"),
    [
        (0, 10, 0.0),
        (5, 10, 0.5),
        (10, 10, 1.0),
        (15, 10, 1.0),  # vượt tổng: kẹp về 1
        (-5, 10, 0.0),  # âm: kẹp về 0, không trả -0,5
        (1, 0, 0.0),  # chưa biết tổng
        (1, -1, 0.0),
    ],
)
def test_fraction_stays_in_range(done: int, total: int, expected: float) -> None:
    assert Progress("tai", done, total).fraction == expected


def test_progress_is_frozen() -> None:
    progress = Progress("tai", 1, 2)
    with pytest.raises(AttributeError):
        progress.done = 5  # type: ignore[misc]


def test_ignore_progress_swallows_everything() -> None:
    """Có sẵn để chữ ký ở lõi không phải nhận `ProgressFn | None` rồi đâu cũng phải kiểm."""
    ignore_progress(Progress("tai", 1, 2))  # không được ném gì
