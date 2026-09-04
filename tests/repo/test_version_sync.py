"""Kho phiên bản, đường MẠNG: tải bản còn thiếu, xác minh, tự chữa, và huỷ được."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from mccore.errors import Cancelled, VersionError
from mccore.model.json_value import JsonValue
from mccore.net.http import HttpClient, RetryPolicy
from mccore.operations.cancellation import CancelToken
from mccore.repo.version_repo import VersionRepository
from mccore.storage.files import atomic_write_json
from mccore.storage.paths import DataPaths
from version_fixtures import load_fixture

MANIFEST_PATH = "/mc/game/version_manifest_v2.json"
FAST_RETRY = RetryPolicy(attempts=2, initial_backoff_seconds=0.01, total_deadline_seconds=5.0)
FABRIC_ID = "fabric-loader-0.19.3-1.21.4"


def write_version(paths: DataPaths, version_id: str) -> None:
    atomic_write_json(paths.version_json(version_id), load_fixture(version_id))


def serve_version(
    state: ServerState, server: LocalHttpsServer, version_id: str
) -> dict[str, JsonValue]:
    """Đưa một phiên bản lên máy chủ test, trả về mục danh mục trỏ tới nó."""
    payload = json.dumps(load_fixture(version_id)).encode("utf-8")
    path = f"/versions/{version_id}.json"
    state.add(path, payload)
    return {
        "id": version_id,
        "type": "release",
        "url": server.url(path),
        "sha1": hashlib.sha1(payload).hexdigest(),
    }


def serve_manifest(state: ServerState, manifest_entries: list[dict[str, JsonValue]]) -> None:
    versions: list[JsonValue] = list(manifest_entries)
    document: JsonValue = {"latest": {"release": "1.21.4"}, "versions": versions}
    state.add(MANIFEST_PATH, json.dumps(document).encode("utf-8"))


def offline_repository(tmp_path: Path) -> VersionRepository:
    return VersionRepository(DataPaths.for_root(tmp_path))


def test_sync_downloads_verifies_and_caches(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    serve_manifest(server_state, [serve_version(server_state, server, "1.20.1")])
    paths = DataPaths.for_root(tmp_path)
    repository = VersionRepository(
        paths, http_client, manifest_url=server.url(MANIFEST_PATH), retry_policy=FAST_RETRY
    )

    version_meta = repository.sync_version_meta("1.20.1")
    assert version_meta.version_id == "1.20.1"
    assert paths.version_json("1.20.1").is_file()

    requests_after_first = server_state.request_count("/versions/1.20.1.json")
    repository.sync_version_meta("1.20.1")
    assert server_state.request_count("/versions/1.20.1.json") == requests_after_first


def test_sync_fetches_every_ancestor(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    serve_manifest(
        server_state,
        [
            serve_version(server_state, server, FABRIC_ID),
            serve_version(server_state, server, "1.21.4"),
        ],
    )
    paths = DataPaths.for_root(tmp_path)
    repository = VersionRepository(
        paths, http_client, manifest_url=server.url(MANIFEST_PATH), retry_policy=FAST_RETRY
    )
    assert repository.sync_version_meta(FABRIC_ID).jar_owner_id == "1.21.4"
    assert paths.version_json("1.21.4").is_file()


def test_a_version_missing_from_the_manifest_says_so(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    serve_manifest(server_state, [serve_version(server_state, server, "1.20.1")])
    repository = VersionRepository(
        DataPaths.for_root(tmp_path),
        http_client,
        manifest_url=server.url(MANIFEST_PATH),
        retry_policy=FAST_RETRY,
    )
    with pytest.raises(VersionError, match="danh mục"):
        repository.sync_raw_version("khong-ton-tai")


def test_a_truncated_file_on_disk_is_replaced(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Một lần Ctrl-C có thể để lại JSON cụt. Giữ nó thì mọi lần chạy sau đều hỏng."""
    serve_manifest(server_state, [serve_version(server_state, server, "1.20.1")])
    paths = DataPaths.for_root(tmp_path)
    atomic_write_json(paths.version_json("1.20.1"), {"id": "1.20.1"})  # thiếu mainClass

    repository = VersionRepository(
        paths, http_client, manifest_url=server.url(MANIFEST_PATH), retry_policy=FAST_RETRY
    )
    assert repository.sync_version_meta("1.20.1").main_class
    assert server_state.request_count("/versions/1.20.1.json") == 1


def test_unparseable_json_on_disk_is_replaced(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    serve_manifest(server_state, [serve_version(server_state, server, "1.20.1")])
    paths = DataPaths.for_root(tmp_path)
    path = paths.version_json("1.20.1")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ khong phai json", encoding="utf-8")

    repository = VersionRepository(
        paths, http_client, manifest_url=server.url(MANIFEST_PATH), retry_policy=FAST_RETRY
    )
    assert repository.sync_version_meta("1.20.1").main_class


def test_a_version_json_that_fails_its_published_sha1_is_refused(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Danh mục công bố sha1 của từng file JSON — chính là để chống file hỏng hoặc bị đổi.

    Không xác minh thì một file sai nằm lại trên đĩa và mọi lần chạy sau đều hỏng theo cách
    khó truy. Đã kiểm bằng đột biến: bỏ xác minh thì trước đây KHÔNG test nào bắt được.
    """
    manifest_entry = serve_version(server_state, server, "1.20.1")
    server_state.add("/versions/1.20.1.json", b'{"id": "1.20.1", "mainClass": "gia-mao"}')
    serve_manifest(server_state, [manifest_entry])

    paths = DataPaths.for_root(tmp_path)
    repository = VersionRepository(
        paths, http_client, manifest_url=server.url(MANIFEST_PATH), retry_policy=FAST_RETRY
    )
    with pytest.raises(Exception, match="sha1"):
        repository.sync_raw_version("1.20.1")
    assert not paths.version_json("1.20.1").exists()


def test_the_retry_policy_actually_reaches_the_downloader(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Một tham số bị bỏ qua âm thầm là lỗi vô hình nếu không có gì khẳng định về nó.

    Đã xảy ra thật: `VersionRepository` nhận `retry_policy` nhưng không truyền xuống
    `download_one`, nên mọi lần tải dùng chính sách mặc định. Chỉ lộ ra khi đo thời gian —
    một test chỉ kiểm "có ném lỗi không" thì vẫn xanh.
    """
    manifest_entry = serve_version(server_state, server, "1.20.1")
    server_state.add("/versions/1.20.1.json", b"khong phai json", fail_first=99)
    serve_manifest(server_state, [manifest_entry])
    paths = DataPaths.for_root(tmp_path)

    repository = VersionRepository(
        paths,
        http_client,
        manifest_url=server.url(MANIFEST_PATH),
        retry_policy=RetryPolicy(attempts=1, initial_backoff_seconds=0.01),
    )
    with pytest.raises(Exception, match="1 lần thử"):
        repository.sync_raw_version("1.20.1")
    assert server_state.request_count("/versions/1.20.1.json") == 1

    server_state.add("/versions/1.20.1.json", b"khong phai json", fail_first=99)
    repository = VersionRepository(
        paths,
        http_client,
        manifest_url=server.url(MANIFEST_PATH),
        retry_policy=RetryPolicy(attempts=3, initial_backoff_seconds=0.01),
    )
    with pytest.raises(Exception, match="3 lần thử"):
        repository.sync_raw_version("1.20.1")
    assert server_state.request_count("/versions/1.20.1.json") == 3


def test_the_manifest_is_fetched_once_per_repository(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Danh mục nặng 268 KB và mất gần một giây; một chuỗi kế thừa tra nhiều bản.

    Nhớ lại trong phạm vi ĐỐI TƯỢNG, không ở mức module: nhớ ở mức module thì hai profile
    chạy song song dùng chung dữ liệu của nhau, và test dính trạng thái của nhau.
    """
    serve_manifest(
        server_state,
        [
            serve_version(server_state, server, FABRIC_ID),
            serve_version(server_state, server, "1.21.4"),
        ],
    )
    repository = VersionRepository(
        DataPaths.for_root(tmp_path),
        http_client,
        manifest_url=server.url(MANIFEST_PATH),
        retry_policy=FAST_RETRY,
    )
    repository.sync_version_meta(FABRIC_ID)
    assert server_state.request_count(MANIFEST_PATH) == 1


def test_cancelling_a_sync_leaves_nothing_behind(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    serve_manifest(server_state, [serve_version(server_state, server, "1.20.1")])
    paths = DataPaths.for_root(tmp_path)
    repository = VersionRepository(
        paths, http_client, manifest_url=server.url(MANIFEST_PATH), retry_policy=FAST_RETRY
    )
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        repository.sync_version_meta("1.20.1", cancel_token=cancel_token)
    assert not paths.version_json("1.20.1").exists()
