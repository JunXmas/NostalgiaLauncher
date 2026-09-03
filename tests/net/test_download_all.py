"""download_all: song song, dedupe, tiến độ, huỷ giữa chừng, và gom lỗi vào báo cáo."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from mccore.errors import Cancelled
from mccore.model.download import Artifact, DownloadTask
from mccore.net.download import download_all
from mccore.net.http import HttpClient, RetryPolicy
from mccore.operations.cancellation import CancelToken
from mccore.operations.progress import Progress

FAST_RETRY = RetryPolicy(attempts=2, initial_backoff_seconds=0.01, total_deadline_seconds=5.0)


def payload_for(index: int) -> bytes:
    return f"noi dung {index}".encode()


def seed(server_state: ServerState, count: int) -> None:
    for index in range(count):
        server_state.add(f"/f{index}", payload_for(index))


def tasks_for(server: LocalHttpsServer, target: Path, count: int) -> list[DownloadTask]:
    return [
        DownloadTask(
            url=server.url(f"/f{index}"),
            destination=target / f"f{index}.bin",
            sha1=hashlib.sha1(payload_for(index)).hexdigest(),
            size=len(payload_for(index)),
        )
        for index in range(count)
    ]


def test_downloads_everything_in_parallel(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    seed(server_state, 24)
    report = download_all(
        client, tasks_for(server, tmp_path, 24), workers=8, retry_policy=FAST_RETRY
    )
    assert report.ok
    assert report.downloaded == 24
    assert report.skipped == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(f"f{i}.bin" for i in range(24))


def test_second_pass_downloads_nothing(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    seed(server_state, 6)
    tasks = tasks_for(server, tmp_path, 6)
    download_all(client, tasks, workers=4, retry_policy=FAST_RETRY)
    report = download_all(client, tasks, workers=4, retry_policy=FAST_RETRY)
    assert report.skipped == 6
    assert report.downloaded == 0
    assert report.bytes_written == 0


def test_duplicate_destinations_are_downloaded_once(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Hai luồng cùng ghi vào một đích là điều kiện đua thật — chỉ mục 1.20.1 có 23 mục trùng."""
    seed(server_state, 1)
    task = tasks_for(server, tmp_path, 1)[0]
    report = download_all(client, [task, task, task], workers=4, retry_policy=FAST_RETRY)
    assert report.downloaded == 1
    assert server_state.request_count("/f0") == 1


def test_progress_is_monotonic_and_reaches_the_total(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    seed(server_state, 12)
    seen: list[Progress] = []
    download_all(
        client,
        tasks_for(server, tmp_path, 12),
        workers=4,
        retry_policy=FAST_RETRY,
        on_progress=seen.append,
    )
    done_values = [progress.done for progress in seen]
    assert done_values == sorted(done_values)
    assert seen[0].done == 0
    assert seen[-1].done == 12
    assert all(progress.total == 12 for progress in seen)
    assert seen[-1].fraction == 1.0


def test_one_failure_does_not_sink_the_whole_batch(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """`doctor` cần biết TẤT CẢ những gì thiếu, và một lỗi không nên xoá công của phần còn lại."""
    seed(server_state, 4)
    tasks = tasks_for(server, tmp_path, 4)
    tasks.append(
        DownloadTask(url=server.url("/khong-co"), destination=tmp_path / "thieu.bin", size=1)
    )
    report = download_all(client, tasks, workers=4, retry_policy=FAST_RETRY)
    assert not report.ok
    assert report.downloaded == 4
    assert len(report.failures) == 1
    assert report.failures[0].task.destination.name == "thieu.bin"
    assert "404" in report.failures[0].reason


def test_cancellation_stops_the_batch(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    seed(server_state, 30)
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        download_all(
            client,
            tasks_for(server, tmp_path, 30),
            workers=4,
            retry_policy=FAST_RETRY,
            cancel_token=cancel_token,
        )


def test_worker_count_must_be_positive(client: HttpClient) -> None:
    with pytest.raises(ValueError, match="số luồng"):
        download_all(client, [], workers=0)


def test_empty_batch_is_fine(client: HttpClient) -> None:
    report = download_all(client, [])
    assert report.ok
    assert (report.downloaded, report.skipped, report.bytes_written) == (0, 0, 0)


def test_artifact_resolves_to_a_task_under_the_root(tmp_path: Path) -> None:
    """`Artifact` khai đường dẫn TƯƠNG ĐỐI; `DownloadTask` mới có đích tuyệt đối."""
    artifact = Artifact(url="https://x/a.jar", relative_path="com/x/a.jar", sha1="ab", size=3)
    task = artifact.to_task(tmp_path)
    assert task.destination == tmp_path / "com" / "x" / "a.jar"
    assert (task.url, task.sha1, task.size) == (artifact.url, artifact.sha1, artifact.size)


def test_artifact_refuses_a_relative_path_that_escapes(tmp_path: Path) -> None:
    from mccore.errors import UnsafePathError

    artifact = Artifact(url="https://x/a", relative_path="../../thoat.jar")
    with pytest.raises(UnsafePathError):
        artifact.to_task(tmp_path)
