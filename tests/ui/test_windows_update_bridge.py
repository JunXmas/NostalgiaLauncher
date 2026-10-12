"""Tải đúng bộ cài qua HTTPS, kiểm hash và giữ launcher mở khi UAC bị huỷ."""

from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn")

from test_bridges import wait_until
from test_update_bridge import wait_for_state

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import UpdateError
from nostalgia.system.platform_info import Platform
from nostalgia.ui.update_bridge import UpdateBridge
from release_fixture import make_bundle, make_launcher, publish_release

pytestmark = pytest.mark.usefixtures("qt_app")
SETUP_NAME = "nostalgia-9.9.9-windows-x64-setup.exe"


def _bridge(server: LocalHttpsServer, tmp_path: Path, certificate: Path) -> UpdateBridge:
    launcher = replace(
        make_launcher(server, tmp_path, certificate),
        platform=Platform(os_name="windows", os_arch="x64", os_version="10"),
    )
    return UpdateBridge(launcher, check_enabled=lambda: False)


def test_windows_downloads_verified_setup_before_requesting_admin_permission(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    payload = b"MZ verified windows installer"
    publish_release(
        server,
        server_state,
        make_bundle("new"),
        extra_assets={"nostalgia_9.9.9_amd64.deb": b"Linux", SETUP_NAME: payload},
    )
    update_bridge = _bridge(server, tmp_path, certificate_pair[0])
    install_dir = tmp_path / "Nostalgia thử ứ"
    with (
        patch("nostalgia.facade.updates.detect_install_kind", return_value="windows-installer"),
        patch("nostalgia.facade.updates.current_install_dir", return_value=install_dir),
        patch("nostalgia.facade.updates.start_windows_installer") as installer,
        patch("nostalgia.facade.updates.install_system_package") as linux_installer,
        patch("os._exit") as exit_launcher,
    ):
        assert update_bridge.property("canSelfUpdate") is True
        update_bridge.checkNow()
        wait_for_state(update_bridge, "available")
        update_bridge.updateNow()
        wait_until(lambda: exit_launcher.called)
        installer.assert_called_once()
        package_path, target = installer.call_args.args
        assert package_path.name == SETUP_NAME and package_path.read_bytes() == payload
        assert target == install_dir
        linux_installer.assert_not_called()
        exit_launcher.assert_called_once_with(0)


def test_cancelled_windows_permission_keeps_current_launcher_running(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    publish_release(server, server_state, make_bundle("new"), extra_assets={SETUP_NAME: b"MZ"})
    update_bridge = _bridge(server, tmp_path, certificate_pair[0])
    with (
        patch("nostalgia.facade.updates.detect_install_kind", return_value="windows-installer"),
        patch(
            "nostalgia.facade.updates.start_windows_installer",
            side_effect=UpdateError(
                "Windows update cancelled. The current launcher is still running."
            ),
        ) as installer,
        patch("nostalgia.facade.updates.install_system_package") as linux_installer,
        patch("os._exit") as exit_launcher,
    ):
        update_bridge.checkNow()
        wait_for_state(update_bridge, "available")
        update_bridge.updateNow()
        wait_for_state(update_bridge, "failed")
        assert "cancelled" in update_bridge.property("message")
        installer.assert_called_once()
        linux_installer.assert_not_called()
        exit_launcher.assert_not_called()


def test_invalid_setup_checksum_never_opens_the_installer_or_exits(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    publish_release(server, server_state, make_bundle("new"), extra_assets={SETUP_NAME: b"MZ"})
    server_state.add("/sums", ("0" * 64 + "  " + SETUP_NAME + "\n").encode())
    update_bridge = _bridge(server, tmp_path, certificate_pair[0])
    with (
        patch("nostalgia.facade.updates.detect_install_kind", return_value="windows-installer"),
        patch("nostalgia.facade.updates.start_windows_installer") as installer,
        patch("os._exit") as exit_launcher,
    ):
        update_bridge.checkNow()
        wait_for_state(update_bridge, "available")
        update_bridge.updateNow()
        wait_for_state(update_bridge, "failed")
        assert "sha256" in update_bridge.property("message")
        installer.assert_not_called()
        exit_launcher.assert_not_called()
