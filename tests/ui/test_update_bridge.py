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


def wait_for_state(update_bridge: UpdateBridge, wanted: str) -> None:
    """Chờ máy trạng thái tới `wanted`; hết giờ thì nói đang kẹt ở đâu, thay vì câu chung chung."""
    try:
        wait_until(lambda: update_bridge.state == wanted)
    except AssertionError as exc:
        message = f"chờ {wanted!r} nhưng kẹt ở {update_bridge.state!r}: {update_bridge.message!r}"
        raise AssertionError(message) from exc


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
    wait_for_state(update_bridge, "available")
    assert update_bridge.latestVersion == "9.9.9" and announced == ["9.9.9"]
    assert update_bridge.releaseNotes == "Ghi chú"

    update_bridge.download()
    wait_for_state(update_bridge, "ready")
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
    wait_until(lambda: update_bridge.state == "upToDate" and not update_bridge.busy)

    server_state.add("/releases/latest", "{ hỏng".encode(), status=500)
    update_bridge.checkNow()
    assert update_bridge.state == "checking", "còn bận thì lệnh trước phải được nhận"
    wait_for_state(update_bridge, "failed")
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


def test_apply_with_no_staged_shows_error_not_silent(
    server: LocalHttpsServer,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Ấn 'Cài và mở lại' khi chưa tải xong phải báo lỗi, không được im lặng (bấm mà không có
    phản hồi gì làm người dùng nghĩ nút bị hỏng)."""
    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    update_bridge = UpdateBridge(launcher, check_enabled=lambda: False)
    assert update_bridge._staged is None

    update_bridge.applyAndRestart()

    assert update_bridge.state == "failed"
    assert update_bridge.message  # không được rỗng


def test_apply_os_error_is_surfaced_not_swallowed(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Nếu write_swap_script hoặc launch_swap_script ném exception hệ thống (PermissionError,
    OSError...), lỗi phải hiện ra ở UI thay vì bị PySide6 nuốt im lặng."""
    from unittest.mock import patch

    publish_release(server, server_state, make_bundle("moi"))
    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    update_bridge = UpdateBridge(launcher, check_enabled=lambda: False)

    update_bridge.checkNow()
    wait_for_state(update_bridge, "available")
    update_bridge.download()
    wait_for_state(update_bridge, "ready")

    # Giả lập launcher bị cài từ gói đóng sẵn nhưng apply_launcher_update ném PermissionError
    # (patch trực tiếp vào facade vì Launcher dùng __slots__ không thể patch.object)
    with patch(
        "nostalgia.facade.updates.UpdateOperations.apply_launcher_update",
        side_effect=PermissionError("không có quyền ghi"),
    ):
        update_bridge.applyAndRestart()

    assert update_bridge.state == "failed"
    assert update_bridge.message  # không được rỗng, lỗi phải hiện cho người dùng


def test_one_button_downloads_then_applies_without_a_second_click(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """`updateNow()` là MỘT nhịp: tải xong tự áp và mở lại, người dùng không bấm nút thứ hai.

    Đây là cả tính năng. Nếu nhịp hai lặng lẽ không chạy, giao diện đứng ở "đã tải xong" và
    người dùng chờ mãi một cái nút đã bị gỡ đi — không gì khác đỏ.
    """
    from unittest.mock import patch

    publish_release(server, server_state, make_bundle("moi"))
    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    update_bridge = UpdateBridge(launcher, check_enabled=lambda: False)
    update_bridge.checkNow()
    wait_for_state(update_bridge, "available")

    applied: list[object] = []

    def record(staged: object) -> Path:
        applied.append(staged)
        return tmp_path / "swap.sh"

    with (
        patch(
            "nostalgia.facade.updates.UpdateOperations.launcher_install_kind", return_value="frozen"
        ),
        patch(
            "nostalgia.facade.updates.UpdateOperations.apply_launcher_update", side_effect=record
        ),
    ):
        update_bridge.updateNow()
        wait_until(lambda: bool(applied))

    assert len(applied) == 1, "phải tự áp đúng một lần sau khi tải xong"


def test_one_button_on_a_package_that_cannot_swap_opens_the_page_instead(
    server: LocalHttpsServer,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Chạy từ mã nguồn (hay .deb/AppImage/macOS .app): tải về rồi mới báo "không tráo được"
    là phí băng thông và làm người dùng cụt hứng. Mở thẳng trang tải."""
    from unittest.mock import patch

    launcher = make_launcher(server, tmp_path, certificate_pair[0])
    update_bridge = UpdateBridge(launcher, check_enabled=lambda: False)

    with patch.object(UpdateBridge, "openReleasePage") as open_page:
        update_bridge.updateNow()

    open_page.assert_called_once()
    assert update_bridge.state == "idle", "không được tải gì khi gói không tự tráo được"
