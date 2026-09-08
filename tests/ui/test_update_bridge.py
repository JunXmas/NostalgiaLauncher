"""Cầu nối cập nhật: máy trạng thái đi đúng đường qua máy chủ giả (kiểm → có bản → tải → sẵn
sàng), công tắc tự kiểm được tôn trọng, và trang CÀI ĐẶT vẽ mục CẬP NHẬT."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject
from test_bridges import wait_until

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.ui.app import build_view
from nostalgia.ui.update_bridge import UpdateBridge
from release_fixture import make_bundle, make_launcher, publish_release

pytestmark = pytest.mark.usefixtures("qt_app")


def test_check_download_and_ready_through_the_bridge(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    publish_release(server, server_state, make_bundle("moi"))
    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    update_bridge = UpdateBridge(launcher, check_enabled=lambda: False)
    announced: list[str] = []
    update_bridge.updateAvailable.connect(announced.append)
    assert (update_bridge.state, update_bridge.installKind) == ("idle", "source")

    update_bridge.checkNow()
    wait_until(lambda: update_bridge.state == "available")
    assert update_bridge.latestVersion == "9.9.9" and announced == ["9.9.9"]
    assert update_bridge.releaseNotes == "Ghi chú"

    update_bridge.download()
    wait_until(lambda: update_bridge.state == "ready")
    assert update_bridge.progressFraction == 1.0
    assert "9.9.9" in update_bridge.message

    update_bridge.applyAndRestart()
    assert update_bridge.state == "failed" and "mã nguồn" in update_bridge.message


def test_up_to_date_and_network_failure_are_reported(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    server_state.add("/releases/latest", b"Not Found", status=404)
    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    update_bridge = UpdateBridge(launcher, check_enabled=lambda: False)
    update_bridge.checkNow()
    wait_until(lambda: update_bridge.state == "upToDate")

    server_state.add("/releases/latest", "{ hỏng".encode(), status=500)
    update_bridge.checkNow()
    wait_until(lambda: update_bridge.state == "failed")
    assert update_bridge.message.startswith("Không kiểm được")


def test_settings_page_shows_the_update_section(tmp_path: Path) -> None:
    from test_qml import make_launcher as make_plain_launcher

    view, _bridge = build_view(make_plain_launcher(tmp_path))
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 6)
    wait_until(lambda: root_item.findChild(QObject, "checkUpdateButton") is not None)
    toggle = root_item.findChild(QObject, "autoUpdateToggle")
    assert toggle is not None and toggle.property("checked") is True
    settings_bridge = view.rootContext().contextProperty("settingsBridge")
    settings_bridge.setAutoUpdateCheck(False)
    wait_until(lambda: toggle.property("checked") is False)
