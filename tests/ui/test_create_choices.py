"""Hộp tạo bản chơi và khối CHƠI: những lựa chọn mà người mới nhìn thấy đầu tiên.

Gác HÀNH VI, không gác toạ độ hay câu chữ: thẻ Optimized là mặc định khi mở, năm loader còn
lại đều có mặt (không cái nào bị giấu trong "nâng cao"), chọn phiên bản Optimized không hỗ trợ
thì GIỮ NGUYÊN lựa chọn và chặn nút tạo, và trang chủ nói rõ thiếu gì thay vì chỉ làm mờ nút.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from modern_window import go, open_modern
from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from test_bridges import wait_until

from nostalgia.api import Launcher

pytestmark = pytest.mark.usefixtures("qt_app")


def open_create_dialog(tmp_path: Path, preset_versions: list[str] | None = None) -> QObject:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view, _bridge, root_item = open_modern(launcher)
    go(root_item, 1, "minimalInstances")
    dialog = root_item.findChild(QObject, "modernCreateDialog")
    assert dialog is not None, "không tìm thấy hộp tạo bản chơi"
    # `openDialog` là hàm QML, mypy không thấy trên QObject.
    dialog.openDialog()  # type: ignore[attr-defined]
    # Mở hộp là bắt đầu tải danh mục; đợi xong (test cô lập mạng nên lỗi nhanh) kẻo nút Tạo
    # còn bị khoá vì "đang tải danh mục".
    catalog_bridge = view.rootContext().contextProperty("catalogBridge")
    wait_until(lambda: not catalog_bridge.busy)
    if preset_versions is not None:
        # Danh sách bản Optimized bình thường tải qua mạng; nhồi thẳng để test không chạm mạng.
        catalog_bridge._preset_versions = preset_versions
        catalog_bridge.presetVersionsChanged.emit()
    QGuiApplication.processEvents()
    return dialog


def test_optimized_is_what_the_dialog_opens_on(tmp_path: Path) -> None:
    """Đề xuất mà phải tự tìm thì không phải đề xuất. Mở ra là nó đã được chọn sẵn."""
    dialog = open_create_dialog(tmp_path)

    assert dialog.property("loaderKind") == "optimized"
    assert dialog.property("isPreset") is True


def test_every_modloader_stays_on_screen(tmp_path: Path) -> None:
    """Fabric/Quilt/Legacy Fabric/Forge/NeoForge/Vanilla phải hiện hết. Giấu một cái vào
    "nâng cao" là người chơi mod tưởng launcher không hỗ trợ nó."""
    dialog = open_create_dialog(tmp_path)

    keys = {choice["key"] for choice in dialog.property("loaderChoices").toVariant()}
    assert {"vanilla", "fabric", "quilt", "legacy_fabric", "forge", "neoforge"} <= keys
    # Chỉ RAM và thư mục được gập lại, và gập sẵn khi mở.
    assert dialog.property("advancedOpen") is False


def test_an_unsupported_version_is_explained_not_erased(tmp_path: Path) -> None:
    """Lỗi cũ: đổi sang Optimized thì `gameVersion` bị xoá ngầm — người dùng thấy lựa chọn của
    mình biến mất mà không ai nói vì sao. Nay giữ nguyên, chặn nút, và nói lý do."""
    dialog = open_create_dialog(tmp_path, preset_versions=["1.21.1"])
    dialog.setProperty("gameVersion", "1.2.3-khong-co-that")
    QGuiApplication.processEvents()

    assert dialog.property("gameVersion") == "1.2.3-khong-co-that", "không được xoá ngầm"
    assert dialog.property("versionUnsupported") is True
    assert dialog.property("canCreate") is False
    assert "1.2.3-khong-co-that" in dialog.property("missingStep")
