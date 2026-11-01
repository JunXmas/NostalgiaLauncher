"""Ô nhập mã phòng ba ô x 6: gõ tự nhảy, dán tự chia, Backspace lùi ô.

Trang chơi chung cũ đã gỡ; component giữ lại cho ô "nhập mã + Vào" ở trang Bạn bè, nên test
dựng thẳng component chứ không qua trang nào.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

from nostalgia.ui.app import QML_DIR

pytestmark = pytest.mark.usefixtures("qt_app")


def test_room_code_boxes_advance_split_paste_and_backspace(tmp_path: Path) -> None:
    """Gõ liền 18 ký tự thường tự nhảy ô và viết hoa; dán chuỗi có gạch tự chia; Backspace ở
    ô rỗng lùi về ô trước."""
    probe = tmp_path / "Probe.qml"
    probe.write_text(
        'import QtQuick\nimport "' + QML_DIR.as_uri() + '"\n'
        'Item { width: 600; height: 120; RoomCodeInput { objectName: "roomCodeField" } }\n',
        encoding="utf-8",
    )
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    view.setSource(QUrl.fromLocalFile(str(probe)))
    assert not view.errors(), [error.toString() for error in view.errors()]
    view.show()
    view.requestActivate()
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None

    def find(name: str) -> QObject:
        found = root_item.findChild(QObject, name)
        assert found is not None, f"không thấy {name}"
        return found

    code_field = find("roomCodeField")
    boxes = [find(f"roomCodeBox{i}") for i in range(3)]
    assert code_field.property("complete") is False

    boxes[0].focusInput()  # type: ignore[attr-defined]
    for character in "k7mpx3q9zvr2tb5hnw":  # QTest.keyClicks chỉ nhận QWidget, không nhận QWindow
        QTest.keyClick(view, character)  # type: ignore[call-overload]
    QGuiApplication.processEvents()
    assert [b.property("text") for b in boxes] == ["K7MPX3", "Q9ZVR2", "TB5HNW"]
    assert code_field.property("code") == "K7MPX3Q9ZVR2TB5HNW"
    assert code_field.property("complete") is True

    code_field.clear()  # type: ignore[attr-defined]
    QGuiApplication.processEvents()
    assert code_field.property("code") == ""
    code_field.setCode(" abcdef-ghjkmn pqrstu ")  # type: ignore[attr-defined]
    QGuiApplication.processEvents()
    assert [b.property("text") for b in boxes] == ["ABCDEF", "GHJKMN", "PQRSTU"]

    boxes[2].setProperty("text", "")
    boxes[2].focusInput()  # type: ignore[attr-defined]
    QTest.keyClick(view, Qt.Key.Key_Backspace)
    QGuiApplication.processEvents()
    assert boxes[1].property("text") == "GHJKM" and boxes[1].property("focused") is True
    view.close()
