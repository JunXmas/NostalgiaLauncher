"""Cầu nối cấp đường dẫn dải sprite khối cho QML.

Sinh dải mất khoảng một giây lần đầu, nên làm ở **luồng nền**: thanh bên hiện glyph chữ
trước, khi dải xong thì đổi sang khối. Mở launcher không bao giờ phải chờ vì mấy cái icon.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal

from nostalgia.ui.blocks import FRAME_COUNT, FRAME_SIZE, ensure_strips
from nostalgia.ui.worker import WorkerBridge

logger = logging.getLogger(__name__)


def newest_client_jar(versions_dir: Path) -> Path | None:
    """Jar client mới nhất người dùng đã tải, hoặc `None` nếu chưa cài bản nào.

    Lấy bản mới nhất theo thời gian sửa: texture của bản mới đầy đủ nhất, và đó cũng là
    bản người dùng vừa đụng tới. Chỉ ĐỌC — không bao giờ ghi vào thư mục versions.

    Nhận thẳng `Path` chứ không nhận `DataPaths`: `tests/test_api_boundary.py` cấm tầng
    giao diện import vào lõi, và ở đây chỉ cần đúng một thư mục.
    """
    if not versions_dir.is_dir():
        return None
    jars = [
        child / f"{child.name}.jar"
        for child in versions_dir.iterdir()
        if child.is_dir() and (child / f"{child.name}.jar").is_file()
    ]
    if not jars:
        return None
    return max(jars, key=lambda jar: jar.stat().st_mtime)


class BlockIconBridge(WorkerBridge):
    """Map `tên khối -> file:// dải sprite`. Rỗng cho tới khi sinh xong."""

    stripsChanged = Signal()

    def __init__(self, data_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._strips: dict[str, str] = {}
        self._cache_dir = data_dir / "cache" / "blocks"
        self._jar = newest_client_jar(data_dir / "versions")
        self.run_in_background(self._generate, "Đang dựng icon khối...")

    def _generate(self) -> None:
        made = ensure_strips(self._cache_dir, self._jar)
        self._strips = {
            name: QUrl.fromLocalFile(str(path)).toString() for name, path in made.items()
        }
        self.stripsChanged.emit()

    @Property("QVariant", notify=stripsChanged)  # type: ignore[arg-type]  # "QVariant" là tên kiểu Qt, mypy chờ một class Python
    def strips(self) -> dict[str, str]:
        return self._strips

    @Property(int, constant=True)
    def frameCount(self) -> int:
        return FRAME_COUNT

    @Property(int, constant=True)
    def frameSize(self) -> int:
        return FRAME_SIZE
