"""Ô CỘNG ĐỒNG ở thanh bên: mở Discord ra trình duyệt, và KHÔNG chuyển trang.

Vì sao đáng có một file riêng: ô này nằm giữa bảy mục điều hướng nhưng thuộc loại khác hẳn —
bấm xong người dùng phải vẫn đứng ở trang cũ. Kiểu lỗi mà nó gác là kiểu im lặng: nhét ô vào
mảng `entries` thì trình biên dịch không kêu gì, app vẫn chạy, chỉ có điều bấm CỘNG ĐỒNG là
nhảy sang một trang trống và cả bảng màu tab dịch đi một nấc.
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
from qml_tree import find_item

from nostalgia.api import Launcher
from nostalgia.ui.app import build_view
from nostalgia.ui.settings_bridge import SettingsBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def build_sidebar(tmp_path: Path) -> tuple[QQuickItem, QObject]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view, _bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    return root_item, sidebar


def test_the_sidebar_has_a_community_link(tmp_path: Path) -> None:
    root_item, _sidebar = build_sidebar(tmp_path)
    assert find_item(root_item, "communityLink") is not None, "thanh bên thiếu ô CỘNG ĐỒNG"


def test_the_community_url_is_the_discord_invite_from_the_python_layer(tmp_path: Path) -> None:
    """Địa chỉ sống ở `repo/endpoints.py`, không phải chuỗi ghi cứng trong QML.

    Gác chuyện dán nhầm hay để trống: ô hiện ra nhưng bấm không đi đâu là lỗi im lặng —
    người dùng tưởng app hỏng chứ không báo cho ai.
    """
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    settings_bridge = SettingsBridge(launcher)

    # `str(...)`: decorator `@Property` của PySide6 khai kiểu trả về là `Property`, nên mypy
    # đọc thuộc tính thành đối tượng chứ không thành chuỗi.
    assert str(settings_bridge.communityUrl) == launcher.community_url()
    assert launcher.community_url().startswith("https://discord.gg/")


def record_opened_urls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Chặn `QDesktopServices.openUrl` lại và ghi địa chỉ ra danh sách.

    Không để Qt mở trình duyệt thật trong test: chạy thật sẽ bật cửa sổ trình duyệt trên máy
    CI và trên máy người chạy test.
    """
    from PySide6.QtGui import QDesktopServices

    opened: list[str] = []
    monkeypatch.setattr(
        QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url.toString()))
    )
    return opened


def test_clicking_the_community_link_opens_the_discord_invite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bấm ô phải gọi đúng cầu nối, và cầu nối phải giao đúng URL cho trình duyệt."""
    opened = record_opened_urls(monkeypatch)
    root_item, _sidebar = build_sidebar(tmp_path)
    link = find_item(root_item, "communityLink")
    assert link is not None

    link.metaObject().invokeMethod(link, "clicked")
    QGuiApplication.processEvents()

    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    assert opened == [launcher.community_url()], "bấm ô CỘNG ĐỒNG không mở lời mời Discord"


def test_clicking_the_community_link_does_not_navigate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LUẬT của ô này: nó là liên kết ra ngoài, không phải điểm đến.

    Bấm xong người dùng vẫn ở trang cũ — `currentIndex` của thanh bên và `Theme.page` (thanh
    bên là nơi DUY NHẤT ghi vào nó) đều không được nhúc nhích. Đây chính là test đỏ lên nếu
    ai đó nhét ô vào mảng `entries`.
    """
    record_opened_urls(monkeypatch)
    root_item, sidebar = build_sidebar(tmp_path)
    # Đứng ở một trang KHÔNG phải trang 0: trang 0 là mặc định nên nếu ô có lỡ đặt lại
    # currentIndex về 0 thì test đứng ở 0 sẽ không thấy gì.
    sidebar.setProperty("currentIndex", 3)
    QGuiApplication.processEvents()
    page_before = theme_page(root_item)
    assert page_before == 3, "thanh bên phải đã kịp nói cho Theme biết đang ở trang 3"

    link = find_item(root_item, "communityLink")
    assert link is not None
    link.metaObject().invokeMethod(link, "clicked")
    QGuiApplication.processEvents()

    assert sidebar.property("currentIndex") == 3, (
        "ô CỘNG ĐỒNG đã đổi trang — nó không phải điểm đến"
    )
    assert theme_page(root_item) == page_before, "ô CỘNG ĐỒNG đã đổi Theme.page"
    assert link.property("selected") is not True, "ô CỘNG ĐỒNG không được sáng lên và ở lại"


def theme_page(root_item: QQuickItem) -> int:
    """`Theme.page` của singleton — đọc qua một biểu thức QML vì singleton không phải con
    của cây item nên `findChild` không với tới.

    `evaluate()` của PySide6 trả về `(giá trị, cờ-lỗi)` chứ không phải mỗi giá trị.
    """
    from PySide6.QtQml import QQmlExpression, qmlContext

    context = qmlContext(root_item)
    assert context is not None
    expression = QQmlExpression(context, root_item, "Theme.page")
    value, _valid = expression.evaluate()
    assert not expression.hasError(), expression.error().toString()
    return int(value)
