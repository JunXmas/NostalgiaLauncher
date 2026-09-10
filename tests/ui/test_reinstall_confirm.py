"""Mod đã có trong bản chơi: nút "Đã cài" xám nhưng vẫn bấm được, và trang THƯ VIỆN hỏi lại
("đã tồn tại") trước khi cài đè; chưa có thì cài thẳng, không hỏi."""

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


def open_library(tmp_path: Path) -> tuple[QObject, QObject, QQuickView]:
    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", LIBRARY_PAGE_INDEX)
    wait_until(lambda: root_item.findChild(QObject, "contentPage") is not None)
    page = root_item.findChild(QObject, "contentPage")
    dialog = root_item.findChild(QObject, "reinstallConfirm")
    assert page is not None and dialog is not None
    return page, dialog, view


def click(view: QQuickView, dialog: QObject, name: str) -> None:
    button = dialog.findChild(QQuickItem, name)
    assert button is not None
    center = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center.toPoint()
    )
    QGuiApplication.processEvents()


def ask_to_install(page: QObject, project_id: str, title: str, *, installed: bool) -> None:
    """Đúng đường mà thẻ/hàng trong lưới đi khi bấm nút Cài."""
    page.requestInstall(project_id, title, installed)  # type: ignore[attr-defined]
    QGuiApplication.processEvents()


def test_an_installed_mod_asks_before_installing_again(tmp_path: Path) -> None:
    page, dialog, view = open_library(tmp_path)
    accepted: list[bool] = []
    dialog.accepted.connect(lambda: accepted.append(True))  # type: ignore[attr-defined]

    ask_to_install(page, "sodium", "Sodium", installed=True)
    assert dialog.property("visible") is True
    message = dialog.findChild(QObject, "confirmMessage")
    assert message is not None and "đã tồn tại" in message.property("text")
    assert "Sodium" in dialog.property("title")
    assert page.property("pendingProjectId") == "sodium"
    assert accepted == [], "chưa đồng ý thì chưa cài"

    click(view, dialog, "confirmAccept")
    assert dialog.property("visible") is False
    assert accepted == [True], "đồng ý → onAccepted gọi contentBridge.install(pendingProjectId)"


def test_cancelling_installs_nothing_and_a_new_mod_never_asks(tmp_path: Path) -> None:
    page, dialog, view = open_library(tmp_path)
    accepted: list[bool] = []
    dialog.accepted.connect(lambda: accepted.append(True))  # type: ignore[attr-defined]

    ask_to_install(page, "iris", "Iris", installed=True)
    assert dialog.property("visible") is True
    click(view, dialog, "confirmCancel")
    assert dialog.property("visible") is False and accepted == []

    ask_to_install(page, "lithium", "Lithium", installed=False)
    assert dialog.property("visible") is False, "mod chưa có thì cài ngay, không hỏi"
    assert accepted == []
