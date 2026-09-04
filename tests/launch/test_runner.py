"""Cài trọn vẹn một phiên bản từ máy chủ giả: mọi mảnh nối đúng thứ tự, không cần Internet."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from fake_mojang import (
    ASSET_BODY,
    CLIENT_BODY,
    JAVA_BODY,
    JAVA_COMPONENT,
    LIBRARY_BODY,
    NATIVE_MEMBER,
    VERSION_ID,
    digest,
    publish,
)
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import Cancelled, NetworkError
from nostalgia.launch.runner import (
    InstallReport,
    install_version,
    resolve_installed_java_binary,
)
from nostalgia.net.http import HttpClient
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress
from nostalgia.storage.paths import DataPaths
from nostalgia.system.platform_info import Platform

LINUX = Platform(os_name="linux", os_arch="x64", os_version="6.8.0")


def install(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    paths: DataPaths,
    **extra: object,
) -> InstallReport:
    return install_version(
        VERSION_ID,
        http_client,
        paths,
        LINUX,
        endpoints=publish(server, server_state),
        **extra,  # type: ignore[arg-type]
    )


def make_paths(tmp_path: Path) -> DataPaths:
    return DataPaths(data_dir=tmp_path / "data", config_dir=tmp_path / "config")


def test_a_full_install_puts_every_piece_where_the_launcher_expects_it(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    paths = make_paths(tmp_path)
    steps: list[Progress] = []

    report = install(server, server_state, http_client, paths, on_progress=steps.append)

    assert paths.version_json(VERSION_ID).is_file()
    assert paths.version_jar(VERSION_ID).read_bytes() == CLIENT_BODY
    assert (paths.libraries_dir / "org/thu/vien/1.0/vien-1.0.jar").read_bytes() == LIBRARY_BODY
    assert (paths.natives_dir(VERSION_ID) / "libthu.so").read_bytes() == NATIVE_MEMBER
    assert paths.asset_object(digest(ASSET_BODY)).read_bytes() == ASSET_BODY
    assert report.java_binary.read_bytes() == JAVA_BODY
    assert report.java_binary.stat().st_mode & stat.S_IXUSR
    assert report.version_meta.version_id == VERSION_ID
    assert report.downloaded > 0
    assert {step.stage for step in steps} >= {"tải", "bung"}


def test_the_flattened_natives_do_not_include_the_excluded_manifest(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    paths = make_paths(tmp_path)
    install(server, server_state, http_client, paths)
    assert [path_entry.name for path_entry in paths.natives_dir(VERSION_ID).iterdir()] == [
        "libthu.so"
    ]


def test_installing_twice_downloads_nothing_the_second_time(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """Đây là lời hứa của cả kho: cài lại khi đã đủ file thì không phát request tải nào.

    Đăng ký máy chủ ĐÚNG MỘT LẦN: mỗi lần `publish` là một `Route` mới với bộ đếm về 0, nên
    publish lại giữa hai lượt sẽ làm phép đếm nói dối.
    """
    paths = make_paths(tmp_path)
    endpoints = publish(server, server_state)
    install_version(VERSION_ID, http_client, paths, LINUX, endpoints=endpoints)
    before = server_state.request_count("/objects/client")

    second = install_version(VERSION_ID, http_client, paths, LINUX, endpoints=endpoints)

    assert server_state.request_count("/objects/client") == before
    assert second.downloaded == 0
    assert second.skipped > 0
    assert second.bytes_written == 0


def test_a_missing_file_on_the_server_stops_the_install_and_names_it(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    endpoints = publish(server, server_state)
    server_state.add("/objects/vien", b"", status=404)

    with pytest.raises(NetworkError, match="vien"):
        install_version(VERSION_ID, http_client, make_paths(tmp_path), LINUX, endpoints=endpoints)


def test_an_install_can_be_cancelled(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        install(server, server_state, http_client, make_paths(tmp_path), cancel_token=cancel_token)


def test_the_java_binary_is_only_found_after_it_is_installed(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """`play` phải chạy được khi không mạng: tìm bản Java trên đĩa, không hỏi Mojang."""
    paths = make_paths(tmp_path)
    report = install(server, server_state, http_client, paths)
    version_meta = report.version_meta

    assert resolve_installed_java_binary(version_meta, LINUX, paths) == report.java_binary
    assert paths.java_runtime_dir(JAVA_COMPONENT, "linux") in report.java_binary.parents

    empty = DataPaths(data_dir=tmp_path / "trong", config_dir=tmp_path / "trong-config")
    assert resolve_installed_java_binary(version_meta, LINUX, empty) is None


def test_nothing_is_written_outside_the_data_directory(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """Luật quan trọng nhất của kho: một lượt cài không được chạm ra ngoài kho của nó."""
    paths = make_paths(tmp_path)
    (tmp_path / "canh-gac").mkdir()

    install(server, server_state, http_client, paths)

    outside = [
        path_entry
        for path_entry in tmp_path.rglob("*")
        if path_entry.is_file() and not path_entry.is_relative_to(paths.data_dir)
    ]
    assert outside == []
    assert not (tmp_path / "config").exists(), "cài đặt không đụng tới thư mục cấu hình"


def test_the_installed_tree_survives_a_second_process(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """Không có file tạm nào nằm lại sau khi cài xong."""
    paths = make_paths(tmp_path)
    install(server, server_state, http_client, paths)

    leftovers = [path_entry for path_entry in paths.data_dir.rglob(".*") if path_entry.is_file()]
    assert leftovers == []
    assert not any(path_entry.name.endswith(".lzma") for path_entry in paths.data_dir.rglob("*"))


def test_the_game_directory_is_only_touched_for_old_style_assets(
    server: LocalHttpsServer, server_state: ServerState, http_client: HttpClient, tmp_path: Path
) -> None:
    """Chỉ mục kiểu mới không cần cây tên, nên không được tạo thư mục game vô cớ."""
    paths = make_paths(tmp_path)
    game_dir = tmp_path / "game"

    install(server, server_state, http_client, paths, game_dir=game_dir)

    assert not game_dir.exists()
    assert not (paths.assets_dir / "virtual").exists(), (
        "chỉ mục kiểu mới không cần cây tên; dựng nó là chép thừa toàn bộ asset lần thứ hai"
    )
    assert os.access(paths.data_dir, os.R_OK)
