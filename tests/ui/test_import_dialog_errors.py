"""Hộp thoại Nhập bản chơi: lỗi của `importBridge` phải lên tới màn hình.

Vì sao đáng có: sau khi nút "Nhập modpack từ file" (chạy qua `contentBridge`) bị gỡ, con
đường chọn file duy nhất còn lại đi qua `importBridge`. `Main.qml` chỉ nối `failed` của
`bridge`, `contentBridge`, `catalogBridge` — nếu quên `importBridge` thì nhập hỏng là một
cú bấm không có chuyện gì xảy ra, không báo, không ghi.
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


def test_a_failed_mrpack_import_reaches_the_banner(tmp_path: Path) -> None:
    """Nhập một file không tồn tại qua importBridge → dải báo lỗi phải hiện chữ."""
    view, _bridge = build_view(make_launcher(tmp_path))
    root_item = view.rootObject()
    assert root_item is not None
    banner = root_item.findChild(QObject, "errorBanner")
    assert banner is not None, "Main.qml phải đặt tên cho dải báo lỗi thì test mới soi được"

    import_bridge = view.rootContext().contextProperty("importBridge")
    import_bridge.importMrpackFile((tmp_path / "khong-co.mrpack").as_uri(), "", "")

    wait_until(lambda: bool(banner.property("message")))
    assert "khong-co.mrpack" in banner.property("message")
