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

from modern_window import go, open_modern
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from nostalgia.api import Launcher
from nostalgia.instance.model import Instance

pytestmark = pytest.mark.usefixtures("qt_app")


def make_launcher(tmp_path: Path) -> Launcher:
    return Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")


def test_the_interface_loads_without_a_single_qml_error(tmp_path: Path) -> None:
    """Không lỗi nạp, và cũng KHÔNG một cảnh báo lúc chạy.

    `view.errors()` chỉ thấy lỗi cú pháp. Một trang thiếu `import "../"` vẫn nạp được, rồi
    kêu `ReferenceError: Theme is not defined` khi dựng — đó là cảnh báo, phải hứng riêng.
    """
    from PySide6.QtCore import qInstallMessageHandler

    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        view, _bridge, root_item = open_modern(make_launcher(tmp_path))
        # Các trang nạp lười, nên phải ghé qua từng trang thì lỗi của trang đó mới lộ.
        for page_index in range(8):
            go(root_item, page_index)
        go(root_item, 0)
    finally:
        qInstallMessageHandler(None)

    assert view.status() == QQuickView.Status.Ready
    assert [error.toString() for error in view.errors()] == []
    assert view.rootObject() is not None
    assert warnings == []


def test_the_interface_renders_to_an_image(qt_app: QGuiApplication, tmp_path: Path) -> None:
    """Nạp được chưa chắc vẽ được. Vẽ ra ảnh mới là bằng chứng."""
    view, _bridge, _root_item = open_modern(make_launcher(tmp_path))
    qt_app.processEvents()

    image = view.grabWindow()

    assert not image.isNull()
    assert image.width() > 800
    assert image.height() > 500


def test_the_bridge_hands_qml_the_real_instances(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="vui-ve", version_id="1.20.1"))
    _view, bridge, _root_item = open_modern(launcher)

    [row] = bridge.instances
    assert (row["instanceId"], row["label"], row["versionId"]) == ("vui-ve", "vui-ve", "1.20.1")
    assert row["gameDir"].endswith("instances/vui-ve")


def test_the_bridge_hands_qml_the_real_accounts(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    launcher.add_offline_account("Jun")
    _view, bridge, _root_item = open_modern(launcher)

    accounts = bridge.accounts

    assert [account["playerName"] for account in accounts] == ["Jun"]
    assert accounts[0]["accountKind"] == "offline"
    assert "access_token" not in accounts[0], "vé đăng nhập không được lọt sang tầng vẽ"
    assert "refreshToken" not in accounts[0]


def test_nothing_is_busy_before_anything_starts(tmp_path: Path) -> None:
    _view, bridge, _root_item = open_modern(make_launcher(tmp_path))

    assert bridge.busy is False
    assert bridge.progressFraction == 0.0


def test_create_button_explains_what_is_missing_and_name_is_optional(tmp_path: Path) -> None:
    """Người dùng bấm "Tạo" mà không thấy gì xảy ra là vì nút bị mờ không lý do. Giờ nút mờ
    phải nói rõ còn thiếu bước nào, và tên để trống thì tự đặt theo loader + phiên bản."""
    from PySide6.QtCore import QObject

    _view, _bridge, root_item = open_modern(make_launcher(tmp_path))
    go(root_item, 1, "minimalInstances")
    dialog = root_item.findChild(QObject, "modernCreateDialog")
    assert dialog is not None
    dialog.openDialog()  # type: ignore[attr-defined]

    assert dialog.property("canCreate") is False
    assert "Minecraft version" in dialog.property("missingStep")

    dialog.setProperty("loaderKind", "forge")
    dialog.setProperty("gameVersion", "1.20.1")
    QGuiApplication.processEvents()
    assert "Forge" in dialog.property("missingStep"), "Forge còn cần chọn bản loader"
    assert dialog.property("defaultName") == "Forge 1.20.1"

    dialog.setProperty("loaderVersion", "1.20.1-47.4.10")
    QGuiApplication.processEvents()
    assert dialog.property("missingStep") == ""


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
