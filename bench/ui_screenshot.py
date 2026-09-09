"""Chụp giao diện ra PNG mà không cần màn hình.

Không phải bench đo tốc độ, nhưng ở cùng chỗ vì cùng mục đích: **biến một thứ chủ quan thành
thứ nhìn được**. Giao diện chỉ có thể nói là đúng khi đã nhìn thấy nó, và ảnh chụp là cách
duy nhất để làm điều đó trong một phiên không có màn hình.

    uv run --extra ui python bench/ui_screenshot.py <thư-mục-dữ-liệu> <ảnh-ra.png>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtGui import QGuiApplication

from nostalgia.api import Launcher
from nostalgia.ui.app import build_view

SETTLE_MILLISECONDS = 1500
GIVE_UP_MILLISECONDS = 20_000


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    data_dir = Path(argv[1])
    output = Path(argv[2])

    qt_application = QGuiApplication(["ui-screenshot"])
    qt_application.setApplicationVersion("0.1.0")
    view, _bridge = build_view(Launcher.for_data_dir(data_dir, data_dir.parent / "config"))
    for error in view.errors():
        print("QML:", error.toString(), file=sys.stderr)
    view.show()

    def shoot() -> None:
        image = view.grabWindow()
        image.save(str(output))
        print(f"đã chụp {output} ({image.width()}x{image.height()})")
        qt_application.quit()

    # Đợi một nhịp cho hoạt ảnh xuất hiện chạy xong, rồi mới chụp.
    QTimer.singleShot(SETTLE_MILLISECONDS, shoot)
    # Phao cứu sinh: không bao giờ để công cụ treo, kể cả khi Qt kẹt.
    QTimer.singleShot(GIVE_UP_MILLISECONDS, qt_application.quit)
    return qt_application.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
