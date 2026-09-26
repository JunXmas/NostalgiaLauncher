"""Thẻ hành tinh: chỉ hiện khi thanh bên thu gọn, đủ sáu đích, hover thì glow.

Tính năng là MẶT KIA của nút thu gọn: thu gọn không được làm mất đường đi nào — sáu mục
chữ của thanh bên phải hiện lại thành sáu thẻ neo vào hành tinh, và bấm thẻ chuyển trang
y như bấm ở thanh bên.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qml_tree import find_item

from nostalgia.api import Launcher
from nostalgia.ui.app import build_view

# Theme.normal — thời lượng Behavior của quầng sáng. Chỉ dùng làm mốc chờ trong test.
Theme_normal_ms = 220

pytestmark = pytest.mark.usefixtures("qt_app")


def build_home(tmp_path: Path) -> tuple[QQuickItem, QObject]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view, _bridge = build_view(launcher)
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    return root_item, sidebar


def planet_cards(root_item: QQuickItem) -> list[QQuickItem]:
    nav = find_item(root_item, "planetNav")
    assert nav is not None
    return [child for child in nav.childItems() if child.objectName() == "planetCard"]


def test_planets_hidden_until_the_sidebar_collapses(tmp_path: Path) -> None:
    root_item, sidebar = build_home(tmp_path)

    nav = find_item(root_item, "planetNav")
    assert nav is not None
    assert not nav.isVisible(), "thanh bên đang mở thì hai đường đi trùng nhau — lỗi 1.0.14 cũ"

    sidebar.setProperty("collapsed", True)
    QGuiApplication.processEvents()
    assert nav.isVisible()

    sidebar.setProperty("collapsed", False)
    QGuiApplication.processEvents()
    assert not nav.isVisible(), "mở thanh bên lại thì thẻ phải nhường chỗ"


def test_six_planet_cards_cover_the_six_sidebar_targets(tmp_path: Path) -> None:
    """Thu gọn không được làm MẤT đường đi: sáu mục ngoài TRANG CHỦ đều phải có thẻ."""
    root_item, sidebar = build_home(tmp_path)
    sidebar.setProperty("collapsed", True)
    QGuiApplication.processEvents()

    targets = sorted(card.property("pageIndex") for card in planet_cards(root_item))
    assert targets == [1, 2, 3, 4, 5, 6]


def test_tapping_a_planet_card_navigates_like_the_sidebar(tmp_path: Path) -> None:
    root_item, sidebar = build_home(tmp_path)
    sidebar.setProperty("collapsed", True)
    QGuiApplication.processEvents()

    settings_card = next(
        card for card in planet_cards(root_item) if card.property("pageIndex") == 6
    )
    settings_card.metaObject().invokeMethod(settings_card, "trigger")
    QGuiApplication.processEvents()

    assert sidebar.property("currentIndex") == 6, "bấm thẻ CÀI ĐẶT phải chuyển trang"


def test_hovering_lights_the_planet_glow(tmp_path: Path) -> None:
    """Glow là phản hồi hover duy nhất trên HÀNH TINH (thẻ có viền + nhấc riêng);
    offscreen không có con chuột nên kích qua `forceGlow` — cùng cờ `lit` với hover."""
    root_item, sidebar = build_home(tmp_path)
    sidebar.setProperty("collapsed", True)
    QGuiApplication.processEvents()

    card = planet_cards(root_item)[0]
    glow = find_item(card, "planetGlow")
    assert glow is not None, "thẻ không có quầng sáng hành tinh"
    assert glow.property("opacity") == 0, "chưa rê chuột thì quầng phải tắt"

    card.setProperty("forceGlow", True)
    # Opacity đi qua Behavior (hoạt ảnh 220 ms) — phải để đồng hồ hoạt ảnh chạy thật,
    # `processEvents` suông không tick animation timer.
    QTest.qWait(Theme_normal_ms + 200)
    assert card.property("lit") is True
    assert glow.property("opacity") > 0.5, "bật lit mà quầng không sáng lên"


def test_collapse_toggle_lives_in_the_sidebar(tmp_path: Path) -> None:
    root_item, sidebar = build_home(tmp_path)
    toggle = root_item.findChild(QObject, "collapseToggle")
    assert toggle is not None, "thanh bên không có nút thu gọn"

    toggle.metaObject().invokeMethod(toggle, "clicked")
    QGuiApplication.processEvents()
    assert sidebar.property("collapsed") is True
