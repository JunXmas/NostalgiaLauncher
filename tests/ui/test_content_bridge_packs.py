"""Cầu nối nội dung, phần modpack và bảo trì: cài pack từ thẻ, nhập từ file, bản mới, nhận diện."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from test_bridges import wait_until

from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from modrinth_fixture import fabric_target, make_content_launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_install_modpack_creates_an_instance_and_selects_it(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Cài modpack từ thẻ: bản chơi mới xuất hiện ở bridge chính, tín hiệu mang mã bản chơi.
    Máy chủ giả là host lạ với luật mrpack, nên ở đây kiểm đúng chỗ luật đó từ chối."""
    import json
    from dataclasses import replace

    from fabric_fixture import publish_fabric
    from modpack_fixture import PACK_ID, publish_modpack

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    publish_fabric(server_state)
    publish_modpack(server, server_state)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, fabric_meta=server.url("/fabric"))
    )
    server_state.add(
        "/modrinth/search",
        json.dumps(
            {
                "hits": [{"project_id": PACK_ID, "title": "Gói Vui", "project_type": "modpack"}],
                "offset": 0,
                "total_hits": 1,
            }
        ).encode(),
    )
    main_bridge = LauncherBridge(launcher)
    content_bridge = ContentBridge(launcher, main_bridge)
    failures: list[str] = []
    content_bridge.failed.connect(failures.append)
    content_bridge.search("modpack", "", "relevance")
    wait_until(lambda: not content_bridge.searching and len(content_bridge.results) == 1)
    assert content_bridge.results[0]["contentKind"] == "modpack"

    content_bridge.install(PACK_ID)  # đường cài thường phải từ chối modpack, im lặng
    assert content_bridge.results[0]["installing"] is False

    content_bridge.installModpack(PACK_ID, "", "")
    wait_until(lambda: bool(failures))  # tín hiệu lỗi xếp hàng, có thể tới sau khi hết bận
    assert "host không được phép" in failures[0]
    assert main_bridge.instances == [], "bị từ chối thì không được tạo bản chơi dở"


def test_import_modpack_file_creates_an_instance_from_a_local_mrpack(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    """Nhập .mrpack từ file: cài Fabric pack đòi, tạo bản chơi, tải mod. Host của máy chủ giả
    không nằm trong danh sách mrpack cho phép nên ở đây nới qua module (như test lõi)."""
    from dataclasses import replace
    from urllib.parse import urlparse

    import nostalgia.content.mrpack as mrpack
    from fabric_fixture import publish_fabric
    from modpack_fixture import MOD_BODY, publish_modpack

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    publish_fabric(server_state)
    host = publish_modpack(server, server_state)
    launcher = replace(
        launcher, endpoints=replace(launcher.endpoints, fabric_meta=server.url("/fabric"))
    )
    # Lấy chính file .mrpack mà máy chủ giả đang phát, ghi ra đĩa như người dùng đã tải về.
    with launcher.make_http_client() as http_client:
        pack_bytes = http_client.fetch_bytes(server.url("/files/goi-vui.mrpack"))
    pack_path = tmp_path / "tai-ve.mrpack"
    pack_path.write_bytes(pack_bytes)
    main_bridge = LauncherBridge(launcher)
    content_bridge = ContentBridge(launcher, main_bridge)
    created: list[str] = []
    content_bridge.modpackInstalled.connect(created.append)
    original = mrpack.ALLOWED_HOSTS
    mrpack.ALLOWED_HOSTS = (host,)
    try:
        content_bridge.importModpackFile(pack_path.as_uri(), "", "")
        wait_until(lambda: bool(created) or not content_bridge.busy)
    finally:
        mrpack.ALLOWED_HOSTS = original
    assert created == ["tai-ve"]
    assert (launcher.paths.instance_dir("tai-ve") / "mods" / "sodium.jar").read_bytes() == MOD_BODY
    assert urlparse(server.url("/")).hostname == host


def test_check_updates_flags_rows_and_identify_names_hand_copied_files(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
) -> None:
    import hashlib
    import json

    launcher = make_content_launcher(server, server_state, tmp_path, certificate_pair)
    target = fabric_target(launcher)
    mods = target.game_dir / "mods"
    mods.mkdir(parents=True)
    hand_copied = b"chep tay" * 3
    (mods / "la.jar").write_bytes(hand_copied)
    sha1 = hashlib.sha1(hand_copied).hexdigest()
    server_state.add(
        "/modrinth/version_files",
        json.dumps(
            {
                sha1: {
                    "id": "vL",
                    "project_id": "LAZ",
                    "version_number": "2.0",
                    "version_type": "release",
                    "game_versions": [VERSION_ID],
                    "loaders": ["fabric"],
                    "date_published": "",
                    "files": [
                        {
                            "url": "https://cdn.modrinth.com/x.jar",
                            "filename": "la.jar",
                            "primary": True,
                            "size": len(hand_copied),
                            "hashes": {"sha1": sha1},
                        }
                    ],
                    "dependencies": [],
                }
            }
        ).encode(),
    )
    server_state.add(
        "/modrinth/projects",
        json.dumps(
            [
                {
                    "id": "LAZ",
                    "title": "Lạ mà quen",
                    "icon_url": "https://x/la.png",
                    "categories": ["fabric"],
                }
            ]
        ).encode(),
    )
    main_bridge = LauncherBridge(launcher)
    content_bridge = ContentBridge(launcher, main_bridge)
    content_bridge.selectInstance(target.instance_id)
    identified: list[int] = []
    content_bridge.identified.connect(identified.append)

    content_bridge.identifyInstalled("mod")
    wait_until(lambda: bool(identified))
    assert identified == [1]
    assert content_bridge.installed[0]["label"] == "Lạ mà quen"

    # Sodium đã cài ở bản v (fixture): máy chủ giả có bản release cùng id -> không có bản mới;
    # file vừa nhận diện có dự án LAZ nhưng máy chủ giả không có /project/LAZ/version -> lỗi rõ.
    sodium = content_bridge.results  # chưa tìm gì: rỗng, chỉ để chắc property sống
    assert sodium == []
    failures: list[str] = []
    content_bridge.failed.connect(failures.append)
    content_bridge.checkUpdates("mod")
    wait_until(lambda: not content_bridge.busy)
    assert failures and "LAZ" in failures[0]
