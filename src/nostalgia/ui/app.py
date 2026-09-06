"""Điểm vào của giao diện: `nostalgia-ui`.

Chỉ làm ba việc — dựng `Launcher`, dựng cầu nối, nạp QML. Mọi logic nằm ở lõi; mọi cách vẽ
nằm ở QML. File này cố ý mỏng để không có chỗ nào cho logic lén chui vào tầng giao diện.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from nostalgia import __version__
from nostalgia.api import Launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import CatalogBridge
from nostalgia.ui.content_bridge import ContentBridge

QML_DIR = Path(__file__).resolve().parent / "qml"


def build_view(launcher: Launcher) -> tuple[QQuickView, LauncherBridge]:
    """Dựng khung nhìn và cầu nối.

    Tách khỏi `main` để test dựng được mà không phải chạy vòng lặp sự kiện — và để bộ chụp
    ảnh dùng lại đúng đường mà người dùng đi, chứ không dựng một bản riêng cho ảnh đẹp.
    """
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    # Gắn cầu nối vào khung nhìn: Qt sẽ huỷ chúng **sau** cây QML, nên không còn cảnh báo
    # "bridge is null" ở những ràng buộc còn sống trong lúc đóng cửa sổ.
    bridge = LauncherBridge(launcher, parent=view)
    context = view.rootContext()
    context.setContextProperty("bridge", bridge)
    context.setContextProperty("contentBridge", ContentBridge(launcher, bridge, parent=view))
    context.setContextProperty("catalogBridge", CatalogBridge(launcher, bridge, parent=view))
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setTitle("Nostalgia Launcher")
    view.resize(1360, 860)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    return view, bridge


def main(argv: list[str] | None = None) -> int:
    """Mở cửa sổ. Trả về mã thoát của vòng lặp sự kiện Qt."""
    qt_application = QGuiApplication(argv if argv is not None else sys.argv)
    qt_application.setApplicationName("Nostalgia Launcher")
    qt_application.setApplicationVersion(__version__)

    view, _bridge = build_view(Launcher.for_environment())
    if view.status() != QQuickView.Status.Ready:
        for error in view.errors():
            print(error.toString(), file=sys.stderr)
        return 1
    view.show()
    return qt_application.exec()


if __name__ == "__main__":
    sys.exit(main())
