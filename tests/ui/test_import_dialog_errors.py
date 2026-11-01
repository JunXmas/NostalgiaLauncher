"""Hộp thoại Nhập bản chơi: lỗi của `importBridge` phải lên tới màn hình.

Vì sao đáng có: con đường chọn file modpack trong hộp Nhập đi qua `importBridge`. Hộp quên
nối `importError` thì nhập hỏng là một cú bấm không có chuyện gì xảy ra, không báo, không ghi.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from modern_window import go, open_modern
from PySide6.QtCore import QObject
from qml_tree import find_item
from test_bridges import wait_until
from test_qml import make_launcher

pytestmark = pytest.mark.usefixtures("qt_app")


def test_a_failed_mrpack_import_reaches_the_dialog(tmp_path: Path) -> None:
    """Nhập một file không tồn tại qua importBridge → dòng trạng thái của hộp phải hiện lỗi."""
    view, _bridge, root_item = open_modern(make_launcher(tmp_path))
    go(root_item, 1, "minimalInstances")
    dialog = root_item.findChild(QObject, "modernImportDialog")
    assert dialog is not None
    dialog.openDialog()  # type: ignore[attr-defined]
    status = find_item(dialog.property("contentItem"), "importStatus") or dialog.findChild(
        QObject, "importStatus"
    )
    assert status is not None

    import_bridge = view.rootContext().contextProperty("importBridge")
    wait_until(lambda: not import_bridge.busy)
    import_bridge.importMrpackFile((tmp_path / "khong-co.mrpack").as_uri(), "", "")

    wait_until(lambda: "khong-co.mrpack" in str(status.property("text")))


def test_a_failed_version_catalog_reaches_the_banner(tmp_path: Path) -> None:
    """Danh mục phiên bản tải hỏng: không báo thì hộp Tạo bản chơi chỉ hiện danh sách rỗng."""
    view, _bridge, root_item = open_modern(make_launcher(tmp_path))
    banner = root_item.findChild(QObject, "errorBanner")
    assert banner is not None
    view.rootContext().contextProperty("catalogBridge").failed.emit("danh mục hỏng")
    wait_until(lambda: banner.property("message") == "danh mục hỏng")
