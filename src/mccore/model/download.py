"""Hai kiểu mô tả một file cần tải, tách rời có chủ ý.

`Artifact` là thứ máy chủ **khai báo**: đường dẫn tương đối, đúng như JSON của Mojang viết.
`DownloadTask` là thứ ta **sẽ làm**: đường dẫn đích tuyệt đối, đã phân giải qua `DataPaths`.

Hai kiểu có trường gần giống nhau nên rất dễ nhập một — đừng. Gộp lại là mất chỗ duy nhất
biết cách đổi đường dẫn tương đối thành đích thật, và tầng thuần sẽ phải biết về đĩa.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mccore.storage.files import resolve_within


@dataclass(frozen=True, slots=True)
class Artifact:
    """Một file tải được, theo khai báo của máy chủ.

    `sha1` và `size` có thể thiếu: một số nguồn không công bố. Khi thiếu, việc xác minh chỉ
    còn dựa vào sự tồn tại của file, nên hãy coi đó là trường hợp kém tin cậy hơn.
    """

    url: str
    relative_path: str
    sha1: str | None = None
    size: int | None = None

    def to_task(self, root: Path) -> DownloadTask:
        """Phân giải thành việc tải cụ thể dưới một thư mục gốc."""
        return DownloadTask(
            url=self.url,
            destination=resolve_within(root, self.relative_path),
            sha1=self.sha1,
            size=self.size,
        )


@dataclass(frozen=True, slots=True)
class DownloadTask:
    """Một việc tải cụ thể: tải `url` về đúng `destination`, rồi xác minh."""

    url: str
    destination: Path
    sha1: str | None = None
    size: int | None = None
