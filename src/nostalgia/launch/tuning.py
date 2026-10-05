"""Tham số bộ nhớ cho máy ảo Java.

Cố tình **rất ít**. Mỗi cờ JVM thêm vào đây phải trả lời được "đo ở đâu ra"; những bộ cờ GC
dài dằng dặc chép qua chép lại trên diễn đàn phần lớn là mê tín, và một cờ sai làm game giật
theo cách rất khó truy. Ai cần cờ riêng thì đưa vào `extra_arguments`.

2048 MB là mặc định của chính trình khởi động Mojang cho bản vanilla. Nó đủ cho 1.20 ở tầm
nhìn mặc định; bản có mod nặng thì người chơi tự nâng.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_MAX_HEAP_MEGABYTES = 2048
DEFAULT_MIN_HEAP_MEGABYTES = 512


@dataclass(frozen=True, slots=True)
class JvmTuning:
    """Bộ nhớ và các cờ JVM do người dùng thêm."""

    max_heap_megabytes: int = DEFAULT_MAX_HEAP_MEGABYTES
    min_heap_megabytes: int = DEFAULT_MIN_HEAP_MEGABYTES
    extra_arguments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Bắt cấu hình vô lý ngay lúc dựng, chứ không để JVM từ chối khởi động rồi mới biết."""
        if self.min_heap_megabytes < 1 or self.max_heap_megabytes < 1:
            message = "bộ nhớ phải lớn hơn 0 MB"
            raise ValueError(message)
        if self.min_heap_megabytes > self.max_heap_megabytes:
            message = (
                f"bộ nhớ tối thiểu ({self.min_heap_megabytes} MB) lớn hơn tối đa "
                f"({self.max_heap_megabytes} MB)"
            )
            raise ValueError(message)

    def to_arguments(self) -> tuple[str, ...]:
        """Cờ người dùng thêm đứng SAU cờ bộ nhớ, để họ ghi đè được mặc định."""
        return (
            f"-Xms{self.min_heap_megabytes}M",
            f"-Xmx{self.max_heap_megabytes}M",
            *self.extra_arguments,
        )
