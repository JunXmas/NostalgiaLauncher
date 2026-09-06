"""Giao diện QML: nạp sạch, không cảnh báo, và cầu nối đưa đúng dữ liệu thật sang.

Vì sao đáng có: một lỗi đánh máy trong QML **không làm chương trình chết** — nó chỉ làm một
binding im lặng trả về `undefined`, và người dùng thấy một ô trống mà không hiểu vì sao. Test
ở đây biến loại lỗi đó thành CI đỏ.

Chạy hoàn toàn không cần màn hình (`QT_QPA_PLATFORM=offscreen`), nên chạy được trên máy chủ CI.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from nostalgia.api import Launcher
from nostalgia.instance.model import Instance
from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def make_launcher(tmp_path: Path) -> Launcher:
    return Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")


def test_the_interface_loads_without_a_single_qml_error(tmp_path: Path) -> None:
    """Không lỗi nạp, và cũng KHÔNG một cảnh báo lúc chạy.

    `view.errors()` chỉ thấy lỗi cú pháp. Một trang thiếu `import "../"` vẫn nạp được, rồi
    kêu `ReferenceError: Theme is not defined` khi dựng — đó là cảnh báo, phải hứng riêng.
    """
    from PySide6.QtCore import QObject, qInstallMessageHandler

    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        view, _bridge = build_view(make_launcher(tmp_path))
        QGuiApplication.processEvents()
        # Các trang nạp lười, nên phải ghé qua từng trang thì lỗi của trang đó mới lộ.
        root_item = view.rootObject()
        assert root_item is not None
        sidebar = root_item.findChild(QObject, "sidebar")
        assert sidebar is not None
        for page_index in range(7):
            sidebar.setProperty("currentIndex", page_index)
            QGuiApplication.processEvents()
        sidebar.setProperty("currentIndex", 0)
    finally:
        qInstallMessageHandler(None)

    assert view.status() == QQuickView.Status.Ready
    assert [error.toString() for error in view.errors()] == []
    assert view.rootObject() is not None
    assert warnings == []


def test_the_interface_renders_to_an_image(qt_app: QGuiApplication, tmp_path: Path) -> None:
    """Nạp được chưa chắc vẽ được. Vẽ ra ảnh mới là bằng chứng."""
    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    qt_app.processEvents()

    image = view.grabWindow()

    assert not image.isNull()
    assert image.width() > 800
    assert image.height() > 500


def test_the_bridge_hands_qml_the_real_instances(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="vui-ve", version_id="1.20.1"))
    _view, bridge = build_view(launcher)

    assert bridge.instances == [{"instanceId": "vui-ve", "label": "vui-ve", "versionId": "1.20.1"}]


def test_the_bridge_hands_qml_the_real_accounts(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.add_offline_account("Jun")
    _view, bridge = build_view(launcher)

    accounts = bridge.accounts

    assert [account["playerName"] for account in accounts] == ["Jun"]
    assert accounts[0]["accountKind"] == "offline"
    assert "access_token" not in accounts[0], "vé đăng nhập không được lọt sang tầng vẽ"
    assert "refreshToken" not in accounts[0]


def test_nothing_is_busy_before_anything_starts(tmp_path: Path) -> None:
    _view, bridge = build_view(make_launcher(tmp_path))

    assert bridge.busy is False
    assert bridge.progressFraction == 0.0


def find_hero_cards(view: QQuickView) -> list[object]:
    from PySide6.QtCore import QObject

    root_item = view.rootObject()
    assert root_item is not None
    return list(root_item.findChildren(QObject, "heroCard"))


def test_every_card_on_the_hero_points_at_a_real_page(tmp_path: Path) -> None:
    """Các thẻ nổi phải bấm được thật, và mỗi thẻ phải dẫn tới ĐÚNG trang của nó.

    Chỉ kiểm "bấm xong có gì đó xảy ra" là chưa đủ: một thẻ dẫn nhầm trang vẫn qua được kiểu
    kiểm đó. Ở đây đọc thẳng đích của từng thẻ.
    """
    view, _bridge = build_view(make_launcher(tmp_path))
    cards = find_hero_cards(view)

    assert len(cards) == 6, "bản mẫu có sáu thẻ nổi"
    targets = sorted(card.property("pageIndex") for card in cards)
    assert targets == [1, 2, 3, 4, 5, 6], "sáu thẻ phải dẫn tới sáu trang khác nhau"
    assert all(card.property("title") for card in cards), "thẻ nào cũng phải có nhãn"


def test_activating_a_card_actually_changes_the_page(tmp_path: Path) -> None:
    """Bấm thẻ phải đổi trang y như bấm ở thanh bên — nếu không thì nó chỉ là hình trang trí."""
    from PySide6.QtCore import QObject

    view, _bridge = build_view(make_launcher(tmp_path))
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None, "không tìm thấy thanh bên"

    cards = find_hero_cards(view)
    multiplayer = next(card for card in cards if card.property("pageIndex") == 5)
    multiplayer.activated.emit()

    assert sidebar.property("currentIndex") == 5


def test_hero_cards_sit_inside_the_photo_and_never_overlap(tmp_path: Path) -> None:
    """Mỗi thẻ neo vào một công trình trong ảnh, nên toạ độ neo phải nằm trong ảnh, và hai
    thẻ không được đè lên nhau — đè là mất chữ, mà chỉ soi mắt mới thấy. Test này thay mắt.
    """
    view, _bridge = build_view(make_launcher(tmp_path))
    cards = find_hero_cards(view)
    rectangles: list[tuple[float, float, float, float]] = []
    for card in cards:
        assert 0.0 < card.property("landmarkX") < 1.0
        assert 0.0 < card.property("landmarkY") < 1.0
        # Chỉ so phần thân thẻ: que nối được phép chạy qua khoảng trống giữa các thẻ.
        left = card.property("x")
        top = card.property("y") + (card.property("stemLength") if card.property("below") else 0)
        rectangles.append(
            (left, top, left + card.property("width"), top + card.property("cardHeight"))
        )

    for index, first in enumerate(rectangles):
        for second in rectangles[index + 1 :]:
            separated = (
                first[2] <= second[0]
                or second[2] <= first[0]
                or first[3] <= second[1]
                or second[3] <= first[1]
            )
            assert separated, f"hai thẻ nổi đè nhau: {first} và {second}"
