"""Ba cầu nối QML ↔ lõi, qua máy chủ giả: kết quả cũ không đè kết quả mới, cài xong sổ cập
nhật, tạo bản chơi ra đúng mã. Chờ luồng nền bằng vòng processEvents có hạn — không ngủ mù."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QGuiApplication

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import make_content_launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import CatalogBridge, slugify

pytestmark = pytest.mark.usefixtures("qt_app")


def wait_until(condition: Callable[[], bool], seconds: float = 10.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        QGuiApplication.processEvents()
        if condition():
            return
        time.sleep(0.01)
    message = "luồng nền không xong trong thời hạn"
    raise AssertionError(message)


def test_catalog_bridge_creates_a_vanilla_instance(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    main_bridge = LauncherBridge(launcher)
    catalog_bridge = CatalogBridge(launcher, main_bridge)
    created: list[str] = []
    catalog_bridge.created.connect(created.append)

    catalog_bridge.loadReleasedVersions()
    wait_until(lambda: len(catalog_bridge.releasedVersions) == 1)
    assert catalog_bridge.releasedVersions[0] == {"versionId": VERSION_ID, "major": "1.99"}

    catalog_bridge.createInstance("Sinh tồn vui!", VERSION_ID, "vanilla", "", 2048)
    wait_until(lambda: bool(created))
    assert created == ["sinh-ton-vui"]
    instance = launcher.list_instances()[0]
    assert (instance.display_name, instance.max_heap_megabytes) == ("Sinh tồn vui!", 2048)
    assert launcher.list_installed_versions() == (VERSION_ID,)


def test_slugify_is_safe_and_unique() -> None:
    assert slugify("Sinh tồn vui!", set()) == "sinh-ton-vui"
    assert slugify("Sinh tồn vui!", {"sinh-ton-vui"}) == "sinh-ton-vui-2"
    assert slugify("...", set()) == "ban-choi"
    assert slugify("-bat-dau-gach", set()) == "bat-dau-gach"
    assert slugify("日本語", set()) == "ban-choi"


def test_microsoft_sign_in_hands_qml_the_device_code_and_activates_the_account(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Mã thiết bị đi ra tín hiệu, tài khoản mới thành tài khoản hoạt động, và play dùng nó."""
    from dataclasses import replace

    import fake_microsoft

    launcher = replace(
        make_content_launcher(server, server_state, tmp_path, certificate_pair),
        auth_endpoints=fake_microsoft.publish(server, server_state),
    )
    main_bridge = LauncherBridge(launcher)
    codes: list[tuple[str, str]] = []
    finished: list[str] = []
    main_bridge.deviceCodeReady.connect(lambda code, url: codes.append((code, url)))
    main_bridge.signInFinished.connect(finished.append)

    main_bridge.signInMicrosoft()
    wait_until(lambda: bool(finished))

    assert codes == [(fake_microsoft.USER_CODE, fake_microsoft.VERIFICATION_URL)]
    assert main_bridge.activePlayerName == finished[0]
    assert [account["accountKind"] for account in main_bridge.accounts] == ["microsoft"]

    main_bridge.addOfflineAccount("Khach")
    wait_until(lambda: len(main_bridge.accounts) == 2)
    assert main_bridge.activePlayerName == "Khach"
    main_bridge.setActiveAccount(finished[0])
    assert main_bridge.activePlayerName == finished[0]
    main_bridge.removeAccount(finished[0])
    wait_until(lambda: len(main_bridge.accounts) == 1)
    assert main_bridge.activePlayerName == "Khach"


def test_play_flags_game_running_and_clears_it_when_the_game_exits(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Popup loading ẩn khi game đang chạy: cờ gameRunning bật sau khi khởi động, tắt khi thoát."""
    from nostalgia.api import Instance

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.install_version(VERSION_ID)
    launcher.create_instance(Instance(instance_id="van", version_id=VERSION_ID))
    launcher.add_offline_account("Jun")
    main_bridge = LauncherBridge(launcher)
    seen: list[str] = []
    # Tín hiệu từ luồng nền xếp hàng sang luồng giao diện, nên chỉ kiểm thứ tự và trạng thái cuối:
    # "java" giả thoát ngay, cờ phải đã tắt khi mọi tín hiệu về tới.
    main_bridge.gameStarted.connect(lambda instance_id: seen.append(f"started={instance_id}"))
    main_bridge.gameStopped.connect(lambda code: seen.append(f"stopped={code}"))

    # Bản cài hụt một thư viện (như Fabric thiếu fabric-loader ngoài đời): nút CHƠI phải tự bù
    # trước khi khởi động, thay vì để JVM chết với mã 1 không log.
    missing_library = next(launcher.paths.libraries_dir.rglob("*.jar"))
    missing_library.unlink()

    main_bridge.play("van")
    wait_until(lambda: len(seen) == 2 and not main_bridge.busy)

    assert missing_library.is_file(), "thư viện thiếu phải được tải lại trước khi chạy"
    assert seen == ["started=van", "stopped=0"]
    assert main_bridge.gameRunning is False
    assert main_bridge.activity.startswith("Khởi động")
    # Phiên chơi được ghi vào thống kê của bản chơi và hàng cho QML thấy ngay.
    assert launcher.describe_instance_stats("van").play.launch_count == 1
    assert main_bridge.instances[0]["launchCount"] == 1


def test_game_failure_message_points_at_the_crash_report() -> None:
    """Game chết thì dải đỏ phải nói mã thoát và nơi xem: báo cáo crash nếu có, không thì
    lỗi Java cuối; không có gì thì chỉ đường tới log."""
    from collections import deque

    from nostalgia.ui.bridge import describe_game_failure

    with_crash = deque(
        [
            "[main/INFO]: bắt đầu",
            "java.lang.UnsatisfiedLinkError: Failed to locate library: liblwjgl.so",
            "#@!@# Game crashed! Crash report saved to: #@!@# /kho/crash-reports/crash-1.txt",
        ]
    )
    assert (
        describe_game_failure(1, with_crash) == "Game thoát (mã 1). /kho/crash-reports/crash-1.txt"
    )

    with_error = deque(["x", "java.lang.OutOfMemoryError: Java heap space", "  at a.b.c"])
    assert describe_game_failure(1, with_error).endswith(
        "java.lang.OutOfMemoryError: Java heap space"
    )

    assert (
        describe_game_failure(137, deque())
        == "Game thoát (mã 137). Xem log trong thư mục bản chơi."
    )
