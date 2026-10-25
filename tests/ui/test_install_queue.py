"""Cài nội dung khi đang chơi và xếp hàng nhiều lượt cài.

Trước đây: game đang chạy (hoặc một lượt cài khác đang tải) là mọi nút Cài bị khoá — người chơi
phải thoát game và cài từng mod một. Cài THÊM file mới là an toàn khi game chạy (có hiệu lực ở
lần mở sau); chỉ gỡ/tắt jar của chính bản đang chạy mới phải đợi.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until

from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import FABRIC_API, LOOPER, SODIUM, fabric_target, make_content_launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


def test_installs_queue_and_work_while_the_game_runs(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    main_bridge = LauncherBridge(launcher)
    content = ContentBridge(launcher, main_bridge)
    content.selectInstance(target.instance_id)
    content.search("mod", "", "relevance")
    wait_until(lambda: not content.busy and len(content.results) == 1)
    # Giả game của chính bản chơi này đang chạy (launch thật cần Java).
    main_bridge._game_running = True
    main_bridge.running_game_dir = str(target.game_dir.resolve())
    main_bridge.gameRunningChanged.emit()
    assert content.inRunningGame is True

    # Thêm một kết quả thứ hai vào danh sách rồi bấm Cài liền hai thẻ: không cái nào bị nuốt.
    looper = (
        launcher.search_content(target, "mod")
        .hits[0]
        .__class__(
            project_id=LOOPER,
            project_slug="a",
            title="A",
            description="",
            author="",
            content_kind="mod",
            icon_url="",
            downloads=0,
            follows=0,
            loaders=("fabric",),
        )
    )
    content._results_model.append([looper])
    content.install(SODIUM)
    content.install(LOOPER)
    assert content.pendingInstalls == 2
    wait_until(lambda: content.pendingInstalls == 0 and not content.busy)

    installed = {m.project_id for m in launcher.list_installed_content(target, "mod")}
    assert {SODIUM, FABRIC_API, LOOPER} <= installed
    # Phụ thuộc chung chỉ hỏi một lần dù hai lượt cài chạy gần như đồng thời.
    assert server_state.request_count(f"/modrinth/project/{FABRIC_API}/version") == 1
    # Mọi luồng nền (cả lượt quét thư mục do cài xong kích hoạt) phải xong trước khi bridge bị thu
    # gom, không thì tín hiệu bắn vào QObject đã huỷ làm sập cả tiến trình test kế tiếp.
    wait_for_background(10)
    wait_until(lambda: not content.busy and not main_bridge.busy)
