"""Báo tiến độ từ lõi ra ngoài.

Lõi không in ra màn hình. Mọi tiến độ đi qua một callback nhận `Progress`, để cùng một hàm
phục vụ được cả CLI lẫn giao diện sau này mà không phải sửa gì.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Progress:
    """Một mốc tiến độ. `total` bằng 0 nghĩa là chưa biết tổng khối lượng."""

    stage: str
    done: int
    total: int

    @property
    def fraction(self) -> float:
        """Tỉ lệ hoàn thành, luôn nằm trong 0..1; trả 0 khi chưa biết tổng.

        Kẹp cả hai đầu chứ không chỉ đầu trên: `done` âm là có thật khi người gọi trừ đi
        phần đã bỏ qua, và một thanh tiến trình nhận -0,5 sẽ vẽ ra thứ vô nghĩa.
        """
        if self.total <= 0:
            return 0.0
        return min(1.0, max(0.0, self.done / self.total))


ProgressFn = Callable[[Progress], None]


def ignore_progress(progress: Progress) -> None:
    """Callback mặc định: không làm gì.

    Có sẵn để người gọi không phải viết `lambda _: None`, và để chữ ký hàm ở lõi không cần
    nhận `ProgressFn | None` rồi đâu đâu cũng phải kiểm `if on_progress is not None`.
    """
