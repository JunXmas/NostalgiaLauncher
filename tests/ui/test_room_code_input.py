"""Ô nhập mã phòng ba ô x 6: gõ tự nhảy, dán tự chia, Backspace lùi ô. Cùng khung dựng với
test_qml.py (build_view + launcher giả), tách file để mỗi file dưới 200 dòng."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication
from test_qml import build_view, make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")


def test_room_code_boxes_advance_split_paste_and_backspace(tmp_path: Path) -> None:
    """Mã phòng nhập qua ba ô x 6: gõ liền 18 ký tự thường tự nhảy ô và viết hoa; dán chuỗi có
    gạch tự chia; Backspace ở ô rỗng lùi về ô trước. Nút Vào phòng chỉ sáng khi đủ 18."""
    from PySide6.QtCore import QObject, Qt
    from PySide6.QtTest import QTest

    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    root_item.findChild(QObject, "sidebar").setProperty("currentIndex", 4)
    for _ in range(50):
        QGuiApplication.processEvents()
        code_field = root_item.findChild(QObject, "roomCodeField")
        if code_field is not None:
            break
    assert code_field is not None
    boxes = [root_item.findChild(QObject, f"roomCodeBox{i}") for i in range(3)]
    join_button = root_item.findChild(QObject, "joinButton")
    assert join_button is not None and join_button.property("clickable") is False

    boxes[0].focusInput()
    for character in "k7mpx3q9zvr2tb5hnw":  # QTest.keyClicks chỉ nhận QWidget, không nhận QWindow
        QTest.keyClick(view, character)
    QGuiApplication.processEvents()
    assert [b.property("text") for b in boxes] == ["K7MPX3", "Q9ZVR2", "TB5HNW"]
    assert code_field.property("code") == "K7MPX3Q9ZVR2TB5HNW"
    assert code_field.property("complete") is True and join_button.property("clickable") is True

    code_field.clear()
    QGuiApplication.processEvents()
    assert code_field.property("code") == ""
    code_field.setCode(" abcdef-ghjkmn pqrstu ")
    QGuiApplication.processEvents()
    assert [b.property("text") for b in boxes] == ["ABCDEF", "GHJKMN", "PQRSTU"]

    boxes[2].setProperty("text", "")
    boxes[2].focusInput()
    QTest.keyClick(view, Qt.Key.Key_Backspace)
    QGuiApplication.processEvents()
    assert boxes[1].property("text") == "GHJKM" and boxes[1].property("focused") is True
