"""Cờ bộ nhớ JVM: ít, và cấu hình vô lý bị chặn ngay lúc dựng."""

from __future__ import annotations

import pytest

from nostalgia.launch.tuning import (
    DEFAULT_MAX_HEAP_MEGABYTES,
    DEFAULT_MIN_HEAP_MEGABYTES,
    JvmTuning,
)


def test_the_default_is_what_mojang_ships() -> None:
    assert JvmTuning().to_arguments() == (
        f"-Xms{DEFAULT_MIN_HEAP_MEGABYTES}M",
        f"-Xmx{DEFAULT_MAX_HEAP_MEGABYTES}M",
    )


def test_user_flags_come_last_so_they_win() -> None:
    """JVM lấy cờ đứng sau khi trùng — đó là cách người dùng nâng bộ nhớ mà không sửa code."""
    arguments = JvmTuning(extra_arguments=("-Xmx8G",)).to_arguments()
    assert arguments[-1] == "-Xmx8G"
    assert arguments.index("-Xmx2048M") < arguments.index("-Xmx8G")


def test_a_minimum_above_the_maximum_is_refused() -> None:
    """JVM sẽ từ chối khởi động với thông báo khó hiểu; báo ở đây thì đọc được."""
    with pytest.raises(ValueError, match="lớn hơn tối đa"):
        JvmTuning(max_heap_megabytes=512, min_heap_megabytes=1024)


@pytest.mark.parametrize(("maximum", "minimum"), [(0, 0), (-1, 512), (2048, 0), (2048, -5)])
def test_a_non_positive_amount_of_memory_is_refused(maximum: int, minimum: int) -> None:
    with pytest.raises(ValueError, match="lớn hơn 0"):
        JvmTuning(max_heap_megabytes=maximum, min_heap_megabytes=minimum)


def test_equal_minimum_and_maximum_is_allowed() -> None:
    """Đặt bằng nhau là cách quen thuộc để tránh JVM phải nới vùng nhớ giữa lúc chơi."""
    assert JvmTuning(max_heap_megabytes=4096, min_heap_megabytes=4096).to_arguments() == (
        "-Xms4096M",
        "-Xmx4096M",
    )
