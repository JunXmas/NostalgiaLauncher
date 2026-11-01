"""Hộp hỏi lại dùng chung (`confirmDialog`): nằm ở cấp cửa sổ nên phủ cả thanh điều hướng; bấm
màn tối hay thanh điều hướng khi hộp đang mở KHÔNG làm gì (jun từng bấm nhầm vì hộp tự đóng);
chỉ Thôi / Esc đóng; đồng ý mới chạy hành động."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from modern_window import go, open_modern
from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_qml import make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")

LIBRARY_PAGE_INDEX = 2
BACKDROP_INSIDE_PAGE = QPointF(400, 60)  # vùng trang phía sau, ngoài hộp


def open_library(tmp_path: Path) -> tuple[QObject, QQuickItem, QQuickView]:
    view, _bridge, root_item = open_modern(make_launcher(tmp_path))
    go(root_item, LIBRARY_PAGE_INDEX)
    dialog = root_item.findChild(QObject, "confirmDialog")
    assert dialog is not None
    return dialog, root_item, view


def click_at(view: QQuickView, point: QPointF) -> None:
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point.toPoint()
    )
    QGuiApplication.processEvents()


def click_button(view: QQuickView, dialog: QObject, name: str) -> None:
    button = dialog.findChild(QQuickItem, name)
    assert button is not None
    click_at(view, button.mapToScene(QPointF(button.width() / 2, button.height() / 2)))


def ask(dialog: QObject, title: str) -> None:
    """Đúng đường mà mọi nút nguy hiểm đi: `confirmDialog.ask(tiêu đề, lời, hành động)`."""
    dialog.ask(title, "Không thể hoàn tác.", None)  # type: ignore[attr-defined]
    QGuiApplication.processEvents()


def test_accepting_runs_the_action(tmp_path: Path) -> None:
    dialog, _root_item, view = open_library(tmp_path)
    done: list[bool] = []
    dialog.accepted.connect(lambda: done.append(True))  # type: ignore[attr-defined]
    ask(dialog, "Xoá Sodium?")
    assert dialog.property("visible") is True
    assert dialog.property("title") == "Xoá Sodium?"
    assert done == [], "chưa đồng ý thì chưa làm"
    click_button(view, dialog, "confirmAccept")
    assert dialog.property("visible") is False
    assert done == [True]


def test_nothing_behind_the_dialog_reacts_and_only_cancel_or_escape_closes_it(
    tmp_path: Path,
) -> None:
    dialog, root_item, view = open_library(tmp_path)
    done: list[bool] = []
    dialog.accepted.connect(lambda: done.append(True))  # type: ignore[attr-defined]
    ask(dialog, "Xoá Iris?")

    click_at(view, BACKDROP_INSIDE_PAGE)
    assert dialog.property("visible") is True, "bấm màn tối không được đóng hộp"
    nav_hit = find_item(root_item, "navigationHit-1")
    assert nav_hit is not None
    click_at(view, nav_hit.mapToScene(QPointF(nav_hit.width() / 2, nav_hit.height() / 2)))
    assert dialog.property("visible") is True and root_item.property("currentIndex") == 2, (
        "thanh điều hướng phải bị hộp phủ — không đổi trang khi đang hỏi"
    )

    click_button(view, dialog, "confirmCancel")
    assert dialog.property("visible") is False and done == []

    ask(dialog, "Xoá Iris?")
    QTest.keyClick(view, Qt.Key.Key_Escape)
    QGuiApplication.processEvents()
    assert dialog.property("visible") is False and done == []
