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

    [row] = bridge.instances
    assert (row["instanceId"], row["label"], row["versionId"]) == ("vui-ve", "vui-ve", "1.20.1")
    assert row["gameDir"].endswith("instances/vui-ve")


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


def test_clicking_a_loader_button_keeps_the_create_dialog_open(tmp_path: Path) -> None:
    """Lỗi thật đã gặp: bấm nút loader trong hộp tạo bản chơi thì hộp đóng luôn, vì TapHandler
    không nuốt sự kiện và cú bấm lọt xuống màn tối "bấm ra ngoài thì đóng". Bấm chuột thật."""
    from PySide6.QtCore import QObject, QPointF, Qt
    from PySide6.QtTest import QTest

    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 1)
    for _ in range(50):  # Loader nạp trang xong mới có hộp thoại
        QGuiApplication.processEvents()
        dialog = root_item.findChild(QObject, "createDialog")
        if dialog is not None:
            break
    assert dialog is not None
    dialog.openDialog()
    QGuiApplication.processEvents()
    assert dialog.property("visible") is True

    loader_row = root_item.findChild(QObject, "loaderRow")
    assert loader_row is not None
    fabric_button = loader_row.childItems()[1]  # Vanilla, Fabric, Forge, NeoForge
    center = fabric_button.mapToScene(
        QPointF(fabric_button.property("width") / 2, fabric_button.property("height") / 2)
    )
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center.toPoint()
    )
    QGuiApplication.processEvents()

    assert dialog.property("loaderKind") == "fabric", "nút loader phải nhận được cú bấm"
    assert dialog.property("visible") is True, "hộp không được đóng khi bấm bên trong"

    # Bấm ra màn tối bên ngoài hộp thì mới đóng.
    QTest.mouseClick(
        view,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPointF(view.width() - 5, 5).toPoint(),
    )
    QGuiApplication.processEvents()
    assert dialog.property("visible") is False


def test_create_button_explains_what_is_missing_and_name_is_optional(tmp_path: Path) -> None:
    """Người dùng bấm "Tạo" mà không thấy gì xảy ra là vì nút bị mờ không lý do. Giờ nút mờ
    phải nói rõ còn thiếu bước nào, và tên để trống thì tự đặt theo loader + phiên bản."""
    from PySide6.QtCore import QObject

    view, _bridge = build_view(make_launcher(tmp_path))
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 1)
    for _ in range(50):
        QGuiApplication.processEvents()
        dialog = root_item.findChild(QObject, "createDialog")
        if dialog is not None:
            break
    assert dialog is not None

    assert dialog.property("canCreate") is False
    assert "phiên bản Minecraft" in dialog.property("missingStep")

    dialog.setProperty("loaderKind", "forge")
    dialog.setProperty("gameVersion", "1.20.1")
    QGuiApplication.processEvents()
    assert "Forge" in dialog.property("missingStep"), "Forge còn cần chọn bản loader"
    assert dialog.property("defaultName") == "Forge 1.20.1"

    dialog.setProperty("loaderVersion", "1.20.1-47.4.10")
    QGuiApplication.processEvents()
    assert dialog.property("missingStep") == ""
    assert dialog.property("canCreate") is True


def test_bench_scripts_build_a_qapplication_not_a_qguiapplication() -> None:
    """`build_view()` tạo `QSystemTrayIcon` — widget, đòi `QApplication`. Bench nào dựng
    `QGuiApplication` sẽ chết ở `QWidget: Cannot create a QWidget without QApplication`, mà
    không test nào bắt được vì test dùng đúng lớp (`tests/conftest.py`). Kiểm tĩnh, vì không
    thể dựng hai QApplication trong cùng một phiên để thử thật."""
    bench_dir = Path(__file__).resolve().parents[2] / "bench"
    scripts = sorted(bench_dir.glob("ui_*.py"))
    assert scripts, f"không thấy bench giao diện nào trong {bench_dir}"
    offenders = [p.name for p in scripts if "QGuiApplication(" in p.read_text(encoding="utf-8")]
    assert not offenders, f"bench dựng QGuiApplication, chết khi build_view tạo tray: {offenders}"
