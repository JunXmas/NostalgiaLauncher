"""MYLA-37: quét không ra gì thì hộp thoại phải nói rõ, không im lặng.

"Không tìm thấy launcher nào trên máy." một mình là ngõ cụt: người dùng đang chạy TLauncher
hay Prism bản Flatpak không biết nên nghĩ máy mình sai hay launcher này không hỗ trợ. Dòng
gợi ý kể tên thứ được hỗ trợ, và chỉ lối thoát `.mrpack` cho launcher ngoài danh sách.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject
from test_bridges import wait_until
from test_qml import make_launcher

from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")

INSTANCES_PAGE_INDEX = 1  # thứ tự trong Sidebar.qml: trang chủ, BẢN CHƠI, thư viện, ...


def test_empty_scan_shows_what_is_supported(tmp_path: Path) -> None:
    """Danh sách quét rỗng → dòng gợi ý hiện, và kể đúng những launcher được hỗ trợ."""
    view, _bridge = build_view(make_launcher(tmp_path))
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", INSTANCES_PAGE_INDEX)
    wait_until(lambda: root_item.findChild(QObject, "importDialog") is not None)

    # Mở hộp thoại rồi sang thẻ "Từ launcher khác": `visible` trong QML tính cả cha, nên
    # dòng gợi ý chỉ "hiện" khi đúng thẻ đó đang mở.
    dialog = root_item.findChild(QObject, "importDialog")
    assert dialog is not None
    dialog.metaObject().invokeMethod(dialog, "openDialog")
    dialog.setProperty("currentTab", 1)

    hint = root_item.findChild(QObject, "scanEmptyHint")
    assert hint is not None, "ImportInstanceDialog.qml phải đặt tên cho dòng gợi ý"
    # Quét chạy ở luồng nền; nhà tạm không có launcher nào nên nó về rỗng rất nhanh.
    wait_until(lambda: bool(hint.property("visible")))

    text = hint.property("text")
    for launcher_name in ("PrismLauncher", "ModrinthApp", "Flatpak", "TLauncher", ".mrpack"):
        assert launcher_name in text, f"dòng gợi ý thiếu {launcher_name}"
