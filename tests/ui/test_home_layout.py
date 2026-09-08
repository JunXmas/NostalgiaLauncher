"""Bố cục trang chủ: thẻ hero không đè cột HỒ SƠ, ô HỒ SƠ cao theo nội dung.

Hai lỗi đã thấy bằng mắt trên máy thật: thẻ TÀI KHOẢN/TÀI NGUYÊN lệch hẳn sang trái ở màn hình
rộng, và ô "Thêm" của HỒ SƠ tràn ra đè lên PHIÊN BẢN ĐÃ TẢI khi có nhiều tài khoản. Test này
thay mắt cho CI.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from test_qml import find_hero_cards, make_launcher

from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def find_item(node: QObject, name: str) -> QObject | None:
    """Delegate của Repeater không có cha QObject (model giữ), nên `findChild` không thấy;
    phải đi theo cây item."""
    if node.objectName() == name:
        return node
    for child in node.childItems():
        found = find_item(child, name)
        if found is not None:
            return found
    return None


def settle(seconds: float = 0.3) -> None:
    """Cho Qt bố cục xong (Repeater dựng hàng, Behavior on height chạy hết) rồi mới đo."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QGuiApplication.processEvents()
        time.sleep(0.01)


def test_hero_cards_stay_clear_of_the_profile_column(tmp_path: Path) -> None:
    """Hai thẻ bên phải từng phải ghim `pivot: 1.0` để né cột HỒ SƠ, và ở màn hình rộng thì
    lệch hẳn sang trái dù thừa chỗ. Nay thẻ tự dịch: ở cửa sổ hẹp không được đè cột, ở cửa sổ
    rộng phải căn giữa công trình (chấm neo nằm quanh giữa thẻ)."""
    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()  # chưa show thì Qt chưa bố cục, đo sẽ ra số rác
    for width in (1280, 1920):
        view.resize(width, 900)
        settle()
        for card in find_hero_cards(view):
            panel = card.property("parent")
            assert abs(panel.property("width") - (width - 232)) < 2, "lớp thẻ phải theo cửa sổ"
            free_right = panel.property("freeRight")
            assert free_right < panel.property("width"), (
                "HeroPanel phải biết cột phải rộng bao nhiêu"
            )
            right = card.property("x") + card.property("width")
            assert right <= free_right + 0.5, (
                f"{card.property('title')} tràn vào cột HỒ SƠ ở {width}px"
            )
            pin_offset = card.property("anchorX") - card.property("x")
            if card.property("anchorX") <= free_right:  # công trình không bị cột che
                assert 0 <= pin_offset <= card.property("width"), (
                    "chấm neo phải nằm trong bề ngang thẻ"
                )
            if width == 1920 and card.property("title") in ("TÀI KHOẢN", "TÀI NGUYÊN"):
                assert abs(pin_offset - card.property("width") / 2) < 4, (
                    f"{card.property('title')} có chỗ mà không căn giữa công trình"
                )


def test_profile_card_grows_with_its_content(tmp_path: Path) -> None:
    """Lỗi đã gặp: ô HỒ SƠ cao theo hằng số, thêm nút thu gọn là ô "Thêm" tràn ra đè lên ô
    PHIÊN BẢN ĐÃ TẢI. Nay ô phải cao đúng bằng nội dung, cả khi thu gọn lẫn khi xoè."""
    launcher = make_launcher(tmp_path)
    for name in ("Jun", "Notch", "Dinnerbone"):
        launcher.add_offline_account(name)
    view, _bridge = build_view(launcher)
    view.show()
    settle()
    root_item = view.rootObject()
    assert root_item is not None
    card = root_item.findChild(QObject, "profileCard")
    column = root_item.findChild(QObject, "profileColumn")
    toggle = find_item(card, "profileChevron")
    assert card is not None and column is not None and toggle is not None

    def content_bottom() -> float:
        return column.property("y") + column.property("implicitHeight") + 18  # Theme.pad

    assert card.property("expanded") is False, "ba tài khoản thì mặc định thu gọn"
    assert toggle.property("visible") is True
    assert content_bottom() <= card.property("height") + 0.5, "nội dung tràn khỏi ô khi thu gọn"

    card.setProperty("expanded", True)
    settle()
    assert content_bottom() <= card.property("height") + 0.5, "nội dung tràn khỏi ô khi xoè"
    assert card.property("height") > 200, "xoè ba hàng thì ô phải cao hơn hẳn"
