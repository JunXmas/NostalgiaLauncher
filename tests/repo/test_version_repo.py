"""Kho phiên bản, đường ĐĨA: đọc, liệt kê, và báo lỗi nêu đúng thứ còn thiếu."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import UnsafePathError, VersionError
from nostalgia.model.json_value import JsonValue
from nostalgia.net.http import RetryPolicy
from nostalgia.repo.version_repo import VersionRepository, is_version_document
from nostalgia.storage.files import atomic_write_json
from nostalgia.storage.paths import DataPaths
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


def test_lists_only_versions_that_have_a_json_on_disk(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    write_version(paths, "1.20.1")
    (paths.versions_dir / "thu-muc-rong").mkdir(parents=True)
    assert VersionRepository(paths).list_installed() == ("1.20.1",)


def test_listing_an_empty_store_is_not_an_error(tmp_path: Path) -> None:
    assert offline_repository(tmp_path).list_installed() == ()


def test_missing_version_names_the_exact_path(tmp_path: Path) -> None:
    """Báo `ConnectionError` khi thiếu file là đẩy người dùng đi sửa mạng.

    Thứ họ cần biết là file nào chưa có. Đây là lỗi launcher tiền nhiệm từng mắc.
    """
    repository = offline_repository(tmp_path)
    with pytest.raises(VersionError, match=r"versions/1\.20\.1/1\.20\.1\.json"):
        repository.load_raw_version("1.20.1")


def test_loading_works_fully_offline(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    write_version(paths, "1.20.1")
    version_meta = offline_repository(tmp_path).load_version_meta("1.20.1")
    assert version_meta.version_id == "1.20.1"
    assert version_meta.java_runtime is not None


def test_offline_inheritance_needs_every_ancestor_on_disk(tmp_path: Path) -> None:
    paths = DataPaths.for_root(tmp_path)
    write_version(paths, FABRIC_ID)
    repository = offline_repository(tmp_path)
    with pytest.raises(VersionError, match=r"1\.21\.4"):
        repository.load_version_meta(FABRIC_ID)
    write_version(paths, "1.21.4")
    assert repository.load_version_meta(FABRIC_ID).jar_owner_id == "1.21.4"


def test_offline_repository_says_so_instead_of_failing_obscurely(tmp_path: Path) -> None:
    with pytest.raises(VersionError, match="ngoại tuyến"):
        offline_repository(tmp_path).sync_raw_version("1.20.1")


def test_a_malicious_version_id_cannot_escape_the_store(tmp_path: Path) -> None:
    """Mã phiên bản đến từ dòng lệnh. Trước khi vá, `/tuyet-doi` ghi ra ngoài thư mục dữ liệu."""
    repository = offline_repository(tmp_path)
    for version_id in ("../../thoat", "/tuyet-doi", "a/b"):
        with pytest.raises(UnsafePathError):
            repository.is_installed(version_id)


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ({"id": "a", "mainClass": "x"}, True),
        ({"id": "a", "inheritsFrom": "b"}, True),
        ({"id": "a"}, False),
        ({"mainClass": "x"}, False),
        ({}, False),
        ("khong phai dict", False),
    ],
)
def test_is_version_document(document: JsonValue, expected: bool) -> None:
    """JSON parse được nhưng thiếu `mainClass` lẫn `inheritsFrom` thì không dùng vào việc gì."""
    assert is_version_document(document) is expected
