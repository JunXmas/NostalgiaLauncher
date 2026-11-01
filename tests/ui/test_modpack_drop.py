"""Kéo-thả modpack vào trang BẢN CHƠI: chỉ file .mrpack/.zip được nhận, và cú thả đi tới đúng
slot nhập modpack với URL của file đó."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from modern_window import go, open_modern
from PySide6.QtCore import QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent, QGuiApplication
from test_bridges import wait_until
from test_qml import make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")


def test_dropped_pack_reaches_the_import_slot(tmp_path: Path) -> None:
    view, _bridge, root_item = open_modern(make_launcher(tmp_path))
    page = go(root_item, 1, "minimalInstances")
    assert go(root_item, 1, "packDropArea") is not None

    modpack_bridge = view.rootContext().contextProperty("contentBridge")
    failures: list[str] = []
    modpack_bridge.failed.connect(failures.append)

    assert page.importDropped(["file:///tmp/anh.png", "file:///tmp/ghi-chu.txt"]) == 0
    assert failures == [], "không phải modpack thì không gọi gì cả"

    missing = tmp_path / "Goi Vui.mrpack"
    assert (
        page.importDropped([QUrl.fromLocalFile(str(missing)).toString(), "file:///tmp/x.zip"]) == 2
    )
    wait_until(lambda: bool(failures))
    assert "Goi Vui.mrpack" in failures[0], "chỉ nhập modpack ĐẦU TIÊN, và đúng file đó"
    assert (
        page.isPackUrl("file:///a/B.MRPACK") is True and page.isPackUrl("file:///a/b.jar") is False
    )


def test_a_real_drag_lights_the_overlay_and_a_drop_imports(tmp_path: Path) -> None:
    view, _bridge, root_item = open_modern(make_launcher(tmp_path))
    drop_zone = go(root_item, 1, "packDropArea")
    failures: list[str] = []
    view.rootContext().contextProperty("contentBridge").failed.connect(failures.append)

    def drag_enter(urls: list[str]) -> QMimeData:
        mime = QMimeData()
        mime.setUrls([QUrl(url) for url in urls])
        QGuiApplication.sendEvent(
            view,
            QDragEnterEvent(
                QPoint(700, 400),
                Qt.DropAction.CopyAction,
                mime,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            ),
        )
        QGuiApplication.processEvents()
        return mime

    drag_enter(["file:///tmp/anh.png"])
    assert drop_zone.property("holdingPack") is False, "kéo ảnh thường thì lớp phủ không sáng"
    QGuiApplication.sendEvent(view, QDragLeaveEvent())
    QGuiApplication.processEvents()

    pack_url = QUrl.fromLocalFile(str(tmp_path / "Goi Vui.mrpack")).toString()
    mime = drag_enter([pack_url])
    assert drop_zone.property("holdingPack") is True, "kéo modpack thì lớp phủ sáng"
    QGuiApplication.sendEvent(
        view,
        QDropEvent(
            QPoint(700, 400),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )
    wait_until(lambda: bool(failures))
    assert "Goi Vui.mrpack" in failures[0]
    assert drop_zone.property("holdingPack") is False
