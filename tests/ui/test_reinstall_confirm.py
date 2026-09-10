"""Hộp hỏi lại "cài thêm mod đã tồn tại": nằm ở cấp cửa sổ nên phủ cả thanh bên; bấm màn tối hay
thanh bên khi hộp đang mở KHÔNG làm gì (jun từng bấm nhầm vì hộp tự đóng); chỉ Thôi / Esc đóng;
đồng ý mới cài. Mod chưa có thì cài thẳng, không hỏi."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_qml import make_launcher

from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")

LIBRARY_PAGE_INDEX = 2
SIDEBAR_INSTANCES_ITEM = QPointF(100, 154)  # mục BẢN CHƠI trên thanh bên
BACKDROP_INSIDE_PAGE = QPointF(300, 120)  # vùng trang phía sau, ngoài hộp


def open_library(tmp_path: Path) -> tuple[QObject, QObject, QObject, QQuickView]:
    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", LIBRARY_PAGE_INDEX)
    wait_until(lambda: root_item.findChild(QObject, "contentPage") is not None)
    page = root_item.findChild(QObject, "contentPage")
    dialog = root_item.findChild(QObject, "confirmDialog")
    assert page is not None and dialog is not None
    return page, dialog, sidebar, view


def click_at(view: QQuickView, point: QPointF) -> None:
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point.toPoint()
    )
    QGuiApplication.processEvents()


def click_button(view: QQuickView, dialog: QObject, name: str) -> None:
    button = dialog.findChild(QQuickItem, name)
    assert button is not None
    click_at(view, button.mapToScene(QPointF(button.width() / 2, button.height() / 2)))


def ask_to_install(page: QObject, project_id: str, title: str, *, installed: bool) -> None:
    """Đúng đường mà thẻ/hàng trong lưới đi khi bấm nút Cài."""
    page.requestInstall(project_id, title, installed)  # type: ignore[attr-defined]
    QGuiApplication.processEvents()


def test_an_installed_mod_asks_before_installing_again(tmp_path: Path) -> None:
    page, dialog, _sidebar, view = open_library(tmp_path)
    accepted: list[bool] = []
    dialog.accepted.connect(lambda: accepted.append(True))  # type: ignore[attr-defined]

    ask_to_install(page, "sodium", "Sodium", installed=True)
    assert dialog.property("visible") is True
    message = dialog.findChild(QObject, "confirmMessage")
    assert message is not None and "đã tồn tại" in message.property("text")
    assert "Sodium" in dialog.property("title") and dialog.property("acceptLabel") == "Cài thêm"
    assert page.property("pendingProjectId") == "sodium"
    assert accepted == [], "chưa đồng ý thì chưa cài"

    click_button(view, dialog, "confirmAccept")
    assert dialog.property("visible") is False
    assert accepted == [True], "đồng ý → hành động cài được gọi rồi mới phát accepted"


def test_nothing_behind_the_dialog_reacts_and_only_cancel_or_escape_closes_it(
    tmp_path: Path,
) -> None:
    page, dialog, sidebar, view = open_library(tmp_path)
    accepted: list[bool] = []
    dialog.accepted.connect(lambda: accepted.append(True))  # type: ignore[attr-defined]
    ask_to_install(page, "iris", "Iris", installed=True)

    click_at(view, BACKDROP_INSIDE_PAGE)
    assert dialog.property("visible") is True, "bấm màn tối không được đóng hộp"
    click_at(view, SIDEBAR_INSTANCES_ITEM)
    assert dialog.property("visible") is True and sidebar.property("currentIndex") == 2, (
        "thanh bên phải bị hộp phủ — không đổi trang khi đang hỏi"
    )

    click_button(view, dialog, "confirmCancel")
    assert dialog.property("visible") is False and accepted == []

    ask_to_install(page, "iris", "Iris", installed=True)
    QTest.keyClick(view, Qt.Key.Key_Escape)
    QGuiApplication.processEvents()
    assert dialog.property("visible") is False and accepted == []

    ask_to_install(page, "lithium", "Lithium", installed=False)
    assert dialog.property("visible") is False, "mod chưa có thì cài ngay, không hỏi"
