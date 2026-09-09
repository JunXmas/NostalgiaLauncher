"""Đo thật hộp Tạo bản chơi: bấm thẻ artwork / chọn phiên bản làm luồng giao diện đứng bao lâu.

Cùng mục đích với `ui_account_probe.py`: biến cảm giác "lag" thành con số. Số liệu trước khi
sửa (09/2026, danh mục giả 100 bản): chọn 1.20.1 đứng 79 ms, chọn 1.16.5 đứng 208 ms — vì
`majorOf()` lặp `catalogBridge.releasedVersions[i]` mà mỗi lần đọc thuộc tính đó là Python
chuyển cả trăm dict sang JS, và 16 thẻ cùng gọi. Sau khi hộp thoại giữ danh mục một lần và
tra bằng bảng: dưới 1 ms.

    uv run --extra ui python bench/ui_create_dialog_probe.py            # offscreen, HOME cách ly
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

WORK_DIR = Path(tempfile.mkdtemp(prefix="nostalgia-probe-dialog-"))
# Đặt HOME trước khi import nostalgia: paths.py tính thư mục cấu hình lúc import.
os.environ["HOME"] = str(WORK_DIR / "home")
os.environ["XDG_CONFIG_HOME"] = str(WORK_DIR / "home/.config")
os.environ["XDG_DATA_HOME"] = str(WORK_DIR / "home/.local/share")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from nostalgia.api import Launcher  # noqa: E402
from nostalgia.ui.app import build_view  # noqa: E402

MAJOR_NAMES = ("26", "1.21", "1.20", "1.19", "1.18", "1.17", "1.16", "1.15", "1.14", "1.13",
               "1.12", "1.11", "1.10", "1.9", "1.8", "1.7")  # fmt: skip


def fake_catalog(limit: int = 100) -> list[dict[str, str]]:
    """Danh mục giả cỡ thật (không chạm mạng): mỗi dòng lớn 7 bản, mới → cũ."""
    rows: list[dict[str, str]] = []
    for major in MAJOR_NAMES:
        for patch_number in range(6, -1, -1):
            version_id = f"{major}.{patch_number}" if patch_number else major
            rows.append({"versionId": version_id, "major": major})
    return rows[:limit]


def main() -> int:
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    launcher = Launcher.for_data_dir(WORK_DIR / "data", WORK_DIR / "config")
    launcher.add_offline_account("JunSlayest")
    qt_application = QGuiApplication(["ui-create-dialog-probe"])
    qt_application.setApplicationVersion("0.0.0")
    view, _bridge = build_view(launcher)
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    catalog_bridge = view.rootContext().contextProperty("catalogBridge")
    catalog_bridge._released = fake_catalog()
    catalog_bridge.releasedVersionsChanged.emit()
    view.show()

    def settle(milliseconds: int) -> float:
        """Xử lý sự kiện một lúc; trả về ms luồng giao diện thực sự bận."""
        deadline = time.perf_counter() + milliseconds / 1000
        busy = 0.0
        while time.perf_counter() < deadline:
            started = time.perf_counter()
            qt_application.processEvents()
            busy += time.perf_counter() - started
            time.sleep(0.002)
        return busy * 1000

    def measure(caption: str, action: Callable[[], object]) -> None:
        started = time.perf_counter()
        action()
        blocked = (time.perf_counter() - started) * 1000
        busy = settle(700)
        print(f"{caption:<20} đứng {blocked:7.1f} ms | luồng chính bận {busy:6.1f} ms / 700")

    sidebar.setProperty("currentIndex", 1)
    settle(600)
    dialog = root_item.findChild(QObject, "createDialog")
    assert dialog is not None
    dialog.openDialog()  # type: ignore[attr-defined]
    settle(800)
    print(f"danh mục: {len(catalog_bridge.releasedVersions)} bản")
    measure("bung thẻ 1.20", lambda: dialog.setProperty("expandedMajor", "1.20"))
    measure("chọn 1.20.1", lambda: dialog.pickGameVersion("1.20.1"))  # type: ignore[attr-defined]
    measure("bung thẻ 1.16", lambda: dialog.setProperty("expandedMajor", "1.16"))
    measure("chọn 1.16.5", lambda: dialog.pickGameVersion("1.16.5"))  # type: ignore[attr-defined]
    measure("thu thẻ", lambda: dialog.setProperty("expandedMajor", ""))
    measure("đứng yên", lambda: None)
    print(f"cảnh báo QML: {len(warnings)}")
    for message in warnings[:5]:
        print("  ", message.split("/qml/")[-1][:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
