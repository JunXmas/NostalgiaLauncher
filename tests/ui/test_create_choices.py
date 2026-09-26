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

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication

from nostalgia.api import Launcher
from nostalgia.instance.model import Instance
from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def open_create_dialog(tmp_path: Path, preset_versions: list[str] | None = None) -> QObject:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view, _bridge = build_view(launcher)
    if preset_versions is not None:
        # Danh sách bản Optimized bình thường tải qua mạng; nhồi thẳng để test không chạm mạng.
        catalog_bridge = view.rootContext().contextProperty("catalogBridge")
        catalog_bridge._preset_versions = preset_versions
        catalog_bridge.presetVersionsChanged.emit()
    root_item = view.rootObject()
    assert root_item is not None
    root_item.findChild(QObject, "sidebar").setProperty("currentIndex", 1)
    QGuiApplication.processEvents()
    dialog = root_item.findChild(QObject, "createDialog")
    assert dialog is not None, "không tìm thấy hộp tạo bản chơi"
    dialog.openDialog()
    QGuiApplication.processEvents()
    return dialog


def test_optimized_is_what_the_dialog_opens_on(tmp_path: Path) -> None:
    """Đề xuất mà phải tự tìm thì không phải đề xuất. Mở ra là nó đã được chọn sẵn."""
    dialog = open_create_dialog(tmp_path)

    assert dialog.property("loaderKind") == "optimized"
    assert dialog.property("isPreset") is True


def test_every_modloader_stays_on_screen(tmp_path: Path) -> None:
    """Fabric/Quilt/Forge/NeoForge/Vanilla phải hiện hết. Giấu một cái vào "nâng cao" là
    người chơi mod tưởng launcher không hỗ trợ nó."""
    dialog = open_create_dialog(tmp_path)

    keys = {choice["key"] for choice in dialog.property("gridChoices").toVariant()}
    assert keys == {"vanilla", "fabric", "quilt", "forge", "neoforge"}
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


def test_the_play_block_says_what_is_missing(tmp_path: Path) -> None:
    """Nút xám câm là lý do người mới bỏ đi: chỗ thêm tài khoản nằm ở trang khác nên họ không
    đoán ra. Khối CHƠI phải nói thiếu gì và đưa luôn nút đi làm việc đó."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    view, _bridge = build_view(launcher)
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    home = root_item.findChild(QObject, "homePage")
    play = root_item.findChild(QObject, "playBlock")
    assert home is not None and play is not None

    assert home.property("missingKind") == "account", "chưa đăng nhập thì hỏi tài khoản trước"
    assert play.findChild(QObject, "missingAction").property("visible") is True

    launcher.create_instance(Instance(instance_id="ban", version_id="1.21.1", display_name="B"))
    _bridge.instancesChanged.emit()
    QGuiApplication.processEvents()
    assert home.property("missingKind") == "account", "có bản chơi rồi vẫn còn thiếu tài khoản"

    launcher.add_offline_account("Jun")
    _bridge.announce_accounts_changed()
    QGuiApplication.processEvents()
    assert home.property("missingKind") == "", "đủ tài khoản và bản chơi thì không còn thiếu gì"
    assert play.findChild(QObject, "missingAction").property("visible") is False


def test_the_sidebar_shows_the_face_from_the_skin_file(tmp_path: Path) -> None:
    """Ô tài khoản góc dưới trái vẽ đầu nhân vật cắt từ chính file skin. Chữ cái đầu chỉ là
    dự phòng cho lúc skin chưa tải xong — hiện cả hai thì thành chữ đè lên mặt."""
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    launcher.add_offline_account("Jun")
    view, _bridge = build_view(launcher)
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    face = root_item.findChild(QObject, "sidebarSkinFace")
    assert face is not None, "không tìm thấy ô mặt ở thanh bên"

    assert face.property("visible") is True, "tài khoản ngoại tuyến vẫn có skin Steve/Alex"
    assert str(face.property("source")).endswith(".png")
    letter = next(
        child
        for child in root_item.findChild(QObject, "sidebarAvatar").children()
        if child.property("text") is not None and str(child.property("text")) == "J"
    )
    assert letter.property("visible") is False, "có mặt rồi thì không vẽ chữ cái đầu nữa"
