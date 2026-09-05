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


@pytest.fixture(scope="session")
def qt_app() -> QGuiApplication:
    """Một `QGuiApplication` cho cả phiên — Qt không cho tạo hai cái."""
    return QGuiApplication.instance() or QGuiApplication(["test"])


@pytest.fixture(autouse=True)
def _qt_ready(qt_app: QGuiApplication) -> None:
    """Mọi test ở đây đều cần Qt sẵn sàng; khai một lần thay vì lặp ở từng chữ ký."""


def make_launcher(tmp_path: Path) -> Launcher:
    return Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")


def test_the_interface_loads_without_a_single_qml_error(tmp_path: Path) -> None:
    view, _bridge = build_view(make_launcher(tmp_path))

    assert view.status() == QQuickView.Status.Ready
    assert [error.toString() for error in view.errors()] == []
    assert view.rootObject() is not None


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
