"""Ba kiểu mô tả một file cần tải, tách nhau theo đúng thứ mà máy chủ có khai hay không.

- `RemoteFile`: url và các số để xác minh. **Chưa biết sẽ lưu ở đâu.**
- `Artifact`: `RemoteFile` mà máy chủ **có** khai đường dẫn tương đối (thư viện, asset).
- `DownloadTask`: việc cụ thể, đích **tuyệt đối** đã phân giải qua `DataPaths`.

Vì sao phải có `RemoteFile` riêng: `downloads.client` và `assetIndex` của Mojang **không**
khai đường dẫn — nơi lưu chúng do bố trí thư mục của launcher quyết định
(`versions/<id>/<id>.jar`, `assets/indexes/<id>.json`). Nếu nhét chúng vào `Artifact` thì
`version/` phải tự dựng chuỗi `"indexes/..."`, và bố trí thư mục có **hai** chỗ định nghĩa.
Đã từng như vậy: `storage/paths.py` và `version/meta.py` cùng biết `indexes/`, và
`DataPaths.asset_index_json` thành hàm không ai gọi. Nay `DataPaths` là nguồn duy nhất.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mccore.storage.files import resolve_within


@dataclass(frozen=True, slots=True)
class RemoteFile:
    """Một file trên máy chủ. `sha1` và `size` có thể thiếu — khi đó xác minh yếu hơn."""

    url: str
    sha1: str | None = None
    size: int | None = None

    def to_task(self, destination: Path) -> DownloadTask:
        """Gắn với một đích tuyệt đối do người gọi chọn."""
        return DownloadTask(url=self.url, destination=destination, sha1=self.sha1, size=self.size)


@dataclass(frozen=True, slots=True)
class Artifact:
    """Một file kèm đường dẫn tương đối **do máy chủ khai**.

    `relative_path` luôn dùng `/` vì nó đến từ JSON; việc đổi sang đường dẫn của hệ thống là
    việc của `resolve_within`, và hàm đó cũng từ chối mọi đường thoát ra ngoài.
    """

    remote: RemoteFile
    relative_path: str

    def to_task(self, parent_dir: Path) -> DownloadTask:
        """Phân giải thành việc tải cụ thể dưới một thư mục cha."""
        return self.remote.to_task(resolve_within(parent_dir, self.relative_path))


@dataclass(frozen=True, slots=True)
class DownloadTask:
    """Một việc tải cụ thể: tải `url` về đúng `destination`, rồi xác minh."""

    url: str
    destination: Path
    sha1: str | None = None
    size: int | None = None
