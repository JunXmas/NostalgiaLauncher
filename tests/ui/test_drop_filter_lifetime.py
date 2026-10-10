"""Qt có thể còn giao sự kiện cho bộ lọc trong lúc wrapper đang được thu hồi."""

from typing import Any

import pytest
from PySide6.QtCore import QEvent, QMimeData, QPoint, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QGuiApplication
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("drag", [False, True])
def test_partially_released_filter_ignores_events_without_its_window(
    preview: Preview, drag: bool
) -> None:
    _launcher, view, _bridge, _root_item = preview
    drop_bridge = view.rootContext().contextProperty("localModBridge")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile("/tmp/example.jar")])
    event: Any = (
        QDragEnterEvent(
            QPoint(20, 20),
            Qt.DropAction.CopyAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        if drag
        else QEvent(QEvent.Type.User)
    )
    owned_view = drop_bridge._view
    del drop_bridge._view
    try:
        # C++ gọi override đang đăng ký, giống vòng đời wrapper trong lỗi CI.
        QGuiApplication.sendEvent(view, event)
    finally:
        drop_bridge._view = owned_view
    assert drop_bridge.property("details")["count"] == 0
