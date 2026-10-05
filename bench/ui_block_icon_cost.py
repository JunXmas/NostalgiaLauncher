"""Đo CPU của icon khối xoay ở thanh bên: lúc rảnh và lúc xoay cả bảy.

Câu hỏi cần trả lời bằng số chứ không bằng cảm giác: thêm bảy icon động vào thanh bên có
làm launcher đốt CPU lúc người dùng không đụng vào không. Đo bằng `time.process_time()`
(CPU của tiến trình) chứ không bằng đồng hồ treo tường — đồng hồ treo tường chỉ nói trôi
bao lâu, không nói tốn bao nhiêu.

    uv run --extra ui python bench/ui_block_icon_cost.py
"""

from __future__ import annotations

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtWidgets import QApplication

from nostalgia.storage.paths import DataPaths
from nostalgia.ui.app import QML_DIR, enable_multisampling
from nostalgia.ui.block_bridge import BlockIconBridge, newest_client_jar

WINDOW = 5.0  # giây mỗi phép đo

SCENE = """
import QtQuick
Column {
    width: 220; height: 340
    property bool go: false
    property int spinCount: 7
    Repeater {
        model: ["grass", "crafting", "bookshelf", "diamond", "command", "chest", "redstone"]
        BlockIcon {
            width: 22; height: 22; block: modelData; glyph: "?"
            spinning: parent.go && index < parent.spinCount
        }
    }
}
"""


def measure(seconds: float) -> float:
    """Phần trăm một lõi mà tiến trình dùng trong `seconds` giây."""
    loop = QEventLoop()
    QTimer.singleShot(int(seconds * 1000), loop.quit)
    cpu, wall = time.process_time(), time.monotonic()
    loop.exec()
    return (time.process_time() - cpu) / (time.monotonic() - wall) * 100


def main() -> int:
    enable_multisampling()
    QApplication(["block-icon-cost"])
    paths = DataPaths.from_env(sys.platform)
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    icons = BlockIconBridge(paths.data_dir)
    engine.rootContext().setContextProperty("blockIcons", icons)

    qml_component = QQmlComponent(engine)
    qml_component.setData(SCENE.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "cost.qml")))
    if qml_component.errors():
        for error in qml_component.errors():
            print("QML:", error.toString(), file=sys.stderr)
        return 1
    scene_root = qml_component.create()
    assert isinstance(scene_root, QQuickItem)

    window = QQuickWindow()
    window.setColor(QColor("#0a0d0b"))
    window.resize(220, 340)
    scene_root.setParentItem(window.contentItem())
    window.show()

    jar = newest_client_jar(paths.versions_dir)
    print(f"jar: {jar if jar else 'không có — dùng texture vẽ bằng code'}")
    measure(2.0)  # chờ dải sinh xong + cảnh dựng xong, không tính vào kết quả

    idle = measure(WINDOW)
    scene_root.setProperty("go", True)
    # Thực tế chỉ MỘT khối xoay một lúc (chuột chỉ ở trên một mục). Bảy khối là cận trên
    # tưởng tượng, đo để biết trần chứ không phải cảnh thường gặp.
    scene_root.setProperty("spinCount", 1)
    one = measure(WINDOW)
    scene_root.setProperty("spinCount", 7)
    seven = measure(WINDOW)
    scene_root.setProperty("go", False)
    settle = measure(WINDOW)

    print(f"rảnh (không rê chuột) : {idle:5.1f}% một lõi")
    print(f"xoay 1 khối (cảnh thật): {one:5.1f}%")
    print(f"xoay cả 7 (cận trên)  : {seven:5.1f}%")
    print(f"sau khi rời chuột     : {settle:5.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
