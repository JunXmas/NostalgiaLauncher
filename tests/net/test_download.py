"""Bộ tải: xác minh, tự chữa, bỏ qua file đã đúng, ghi nguyên tử, huỷ được."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from mccore.model.download import DownloadTask
from mccore.net.download import download_one, is_already_correct
from mccore.net.http import HttpClient, RetryPolicy

FAST_RETRY = RetryPolicy(attempts=3, initial_backoff_seconds=0.01, total_deadline_seconds=5.0)
PAYLOAD = b"noi dung that"
PAYLOAD_SHA1 = hashlib.sha1(PAYLOAD).hexdigest()


def make_task(
    server: LocalHttpsServer, path: str, destination: Path, **overrides: object
) -> DownloadTask:
    fields: dict[str, object] = {"sha1": PAYLOAD_SHA1, "size": len(PAYLOAD)}
    fields.update(overrides)
    return DownloadTask(url=server.url(path), destination=destination, **fields)  # type: ignore[arg-type]


def test_downloads_and_verifies(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    server_state.add("/a", PAYLOAD)
    task = make_task(server, "/a", tmp_path / "a.bin")
    assert download_one(client, task, retry_policy=FAST_RETRY) == len(PAYLOAD)
    assert task.destination.read_bytes() == PAYLOAD


def test_skips_when_already_correct(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Lần cài thứ hai phải không phát request nào — luật 8 ở docs/PERFORMANCE.md."""
    server_state.add("/a", PAYLOAD)
    task = make_task(server, "/a", tmp_path / "a.bin")
    download_one(client, task, retry_policy=FAST_RETRY)
    assert server_state.request_count("/a") == 1
    assert download_one(client, task, retry_policy=FAST_RETRY) == 0
    assert server_state.request_count("/a") == 1


def test_repairs_a_file_of_the_wrong_size(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    server_state.add("/a", PAYLOAD)
    task = make_task(server, "/a", tmp_path / "a.bin")
    task.destination.write_bytes(b"rac")
    assert download_one(client, task, retry_policy=FAST_RETRY) == len(PAYLOAD)
    assert task.destination.read_bytes() == PAYLOAD


def test_wrong_sha1_from_the_server_is_refused(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Máy chủ trả nội dung khác với sha1 nó công bố: không được lưu, và phải nói rõ sha1."""
    server_state.add("/a", b"noi dung khac")
    task = make_task(server, "/a", tmp_path / "a.bin", size=None)
    with pytest.raises(Exception, match="sha1"):
        download_one(client, task, retry_policy=FAST_RETRY)
    assert not task.destination.exists()
    assert list(tmp_path.iterdir()) == []


def test_transient_failures_are_retried(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    server_state.add("/a", PAYLOAD, fail_first=2)
    task = make_task(server, "/a", tmp_path / "a.bin")
    assert download_one(client, task, retry_policy=FAST_RETRY) == len(PAYLOAD)


def test_no_temporary_file_is_left_behind_on_failure(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    server_state.add("/a", b"", status=500)
    task = make_task(server, "/a", tmp_path / "a.bin")
    with pytest.raises(Exception, match="500"):
        download_one(client, task, retry_policy=FAST_RETRY)
    assert list(tmp_path.iterdir()) == []


def test_parent_directories_are_created(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    server_state.add("/a", PAYLOAD)
    task = make_task(server, "/a", tmp_path / "sau" / "hon" / "a.bin")
    download_one(client, task, retry_policy=FAST_RETRY)
    assert task.destination.read_bytes() == PAYLOAD


def test_is_already_correct_handles_missing_size(tmp_path: Path) -> None:
    """Không có kích thước công bố thì chỉ còn dựa vào sự tồn tại — kém tin cậy hơn."""
    destination = tmp_path / "a.bin"
    task = DownloadTask(url="https://x/a", destination=destination)
    assert is_already_correct(task) is False
    destination.write_bytes(b"gi cung duoc")
    assert is_already_correct(task) is True


@pytest.mark.network
def test_reaches_the_real_mojang_manifest() -> None:
    """Đường thật, CDN thật. Bỏ qua khi chạy offline; CI có workflow riêng cho nhóm này."""
    real_client = HttpClient(timeout_seconds=30.0)
    try:
        manifest = real_client.fetch_bytes(
            "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
        )
    finally:
        real_client.close()
    parsed = json.loads(manifest)
    assert "latest" in parsed
    assert parsed["versions"], "manifest phải liệt kê ít nhất một phiên bản"
