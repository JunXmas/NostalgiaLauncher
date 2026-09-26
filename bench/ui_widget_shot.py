"""Chụp một widget QML lẻ ra PNG, kể cả GIỮA CHỪNG hoạt ảnh.

`ui_screenshot.py` dựng cả cửa sổ rồi chụp một lần sau 1,5 giây — hợp để soi bố cục,
vô dụng để soi chuyển động. Ở đây chụp nhiều mốc thời gian của một đoạn QML nhỏ, ghép
thành một dải ngang: nhìn một ảnh là thấy cả đường đi của hoạt ảnh.

    uv run --extra ui python bench/ui_widget_shot.py <ảnh-ra.png> <mốc,ms,…> <<'QML'
    import QtQuick
    Item { width: 200; height: 60; CheckRow { ... } }
    QML
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer, QUrl
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtWidgets import QApplication

from nostalgia.ui.app import QML_DIR, enable_multisampling

BACKGROUND = QColor("#0a0d0b")


def wait(milliseconds: int) -> None:
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    output, stops = Path(argv[1]), [int(part) for part in argv[2].split(",")]
    source = sys.stdin.read()

    enable_multisampling()
    QApplication(["ui-widget-shot"])
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    qml_component = QQmlComponent(engine)
    qml_component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "shot.qml")))
    if qml_component.errors():
        for error in qml_component.errors():
            print("QML:", error.toString(), file=sys.stderr)
        return 1
    scene_root = qml_component.create()
    assert isinstance(scene_root, QQuickItem)

    window = QQuickWindow()
    window.setColor(BACKGROUND)
    window.resize(int(scene_root.width()), int(scene_root.height()))
    scene_root.setParentItem(window.contentItem())
    window.show()
    wait(300)  # một nhịp cho cảnh dựng xong trước khi bấm giờ

    frames: list[QImage] = []
    previous = 0
    for stop in stops:
        wait(max(0, stop - previous))
        previous = stop
        frames.append(window.grabWindow())

    # Ghép ngang, cách nhau 8 px nền để thấy rõ ranh giới từng mốc.
    gap = 8
    width = sum(frame.width() for frame in frames) + gap * (len(frames) - 1)
    strip = QImage(width, frames[0].height(), QImage.Format.Format_RGB32)
    strip.fill(BACKGROUND)
    painter = QPainter(strip)
    x = 0
    for frame in frames:
        painter.drawImage(x, 0, frame)
        x += frame.width() + gap
    painter.end()
    strip.save(str(output))
    print(f"đã chụp {output} — {len(frames)} mốc: {stops}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
