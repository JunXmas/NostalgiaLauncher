"""Thẻ bản chơi phải là KHỐI, cùng công thức với Panel — không phải mảng màu phẳng.

Gác hành vi đo được, không gác toạ độ hay sắc độ cụ thể: thẻ có cạnh dưới dày (thứ làm nó
đọc ra khối đặc), và cạnh đó phải TÁCH được khỏi nét mực bao ngoài. Lỗi cũ lặng lẽ nhất là
tô cạnh bằng một xám gần trùng nét mực: mã trông vẫn đúng, ảnh chụp ra thì cạnh biến mất.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtQml import QQmlProperty
from qml_tree import find_item

from nostalgia.api import Launcher
from nostalgia.instance.model import Instance
from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def build_page_with_a_card(tmp_path: Path) -> QObject:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    launcher.create_instance(Instance(instance_id="ban", version_id="1.21.1", display_name="B"))
    view, _bridge = build_view(launcher)
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 1)
    QGuiApplication.processEvents()
    edge = find_item(root_item, "cardEdge")
    assert edge is not None, "thẻ bản chơi không có cạnh dưới — nó lại thành mảng phẳng"
    return edge


def test_the_card_has_a_thick_bottom_edge(tmp_path: Path) -> None:
    """Bề dày cạnh là thứ nói "khối đặc"; chuyển sắc chỉ nói "có ánh sáng"."""
    edge = build_page_with_a_card(tmp_path)

    assert edge.property("height") >= 4, "cạnh mỏng dưới 4 px thì mắt đọc ra đường kẻ"


def test_the_edge_stays_visible_against_the_ink_outline(tmp_path: Path) -> None:
    """Cạnh và nét mực nằm sát nhau. Cùng sắc độ thì cạnh biến mất — chỉ thấy khi chụp ảnh."""
    edge = build_page_with_a_card(tmp_path)
    card = edge.parent()
    assert card is not None

    edge_colour = QColor(edge.property("color"))
    # `card.property("border")` trả về QQuickPen, PySide6 không đổi sang Python được.
    ink_colour = QColor(QQmlProperty.read(card, "border.color"))
    gap = abs(edge_colour.lightness() - ink_colour.lightness())
    assert gap >= 8, f"cạnh và nét mực chênh nhau {gap}/255 độ sáng — nhìn ra một mảng"
