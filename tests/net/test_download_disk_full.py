"""Tải file khi ổ đĩa đầy: đảm bảo ném `DiskFullError`, không retry vô hạn."""

from __future__ import annotations

import errno
import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import DiskFullError
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_one
from nostalgia.net.http import HttpClient
from nostalgia.net.retry import RetryPolicy

FAST_RETRY = RetryPolicy(attempts=4, initial_backoff_seconds=0.01, total_deadline_seconds=5.0)
PAYLOAD = b"noi dung that" * 100  # đủ lớn để có ít nhất một khối ghi
PAYLOAD_SHA1 = hashlib.sha1(PAYLOAD).hexdigest()


def _make_task(server: LocalHttpsServer, destination: Path) -> DownloadTask:
    return DownloadTask(
        url=server.url("/bigfile"),
        destination=destination,
        sha1=PAYLOAD_SHA1,
        size=len(PAYLOAD),
    )


def test_disk_full_raises_disk_full_error_not_network_error(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Khi ghi file gặp ENOSPC, phải ném DiskFullError — KHÔNG phải NetworkError."""
    server_state.add("/bigfile", PAYLOAD)
    task = _make_task(server, tmp_path / "out.bin")

    call_count = 0
    real_write = None

    class FakeHandle:
        """Bọc file handle thật, ném OSError(ENOSPC) ngay lần write đầu tiên."""

        def __init__(self, real: object) -> None:
            self._real = real

        def write(self, content: bytes) -> int:
            nonlocal call_count
            call_count += 1
            error = OSError(errno.ENOSPC, "No space left on device")
            error.errno = errno.ENOSPC
            raise error

        def __getattr__(self, name: str) -> object:
            return getattr(self._real, name)

        def __enter__(self) -> FakeHandle:
            return self

        def __exit__(self, *args: object) -> None:
            self._real.close()

    import builtins

    original_fdopen = __import__("os").fdopen

    def patched_fdopen(fd: int, mode: str = "r", *args: object, **kwargs: object) -> object:
        real = original_fdopen(fd, mode, *args, **kwargs)
        if "w" in mode:
            return FakeHandle(real)
        return real

    with patch("os.fdopen", side_effect=patched_fdopen):
        with pytest.raises(DiskFullError, match="ổ đĩa đầy"):
            download_one(http_client, task, retry_policy=FAST_RETRY)

    # Không được retry: lỗi đĩa đầy là vĩnh viễn, retry chỉ lãng phí.
    assert call_count == 1, f"retry đã chạy {call_count} lần, kỳ vọng chỉ 1"

    # File tạm phải được dọn sạch.
    assert not task.destination.exists()
    remaining = [f for f in tmp_path.iterdir() if not f.name.startswith(".nfs")]
    assert remaining == [], f"file tạm còn sót: {remaining}"


def test_disk_full_does_not_retry(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Xác minh rằng retry module bỏ qua DiskFullError — chỉ retry NetworkError/IntegrityError."""
    server_state.add("/bigfile", PAYLOAD)
    task = _make_task(server, tmp_path / "out.bin")
    attempt_count = 0

    import os as _os

    original_fdopen = _os.fdopen

    def counting_fdopen(fd: int, mode: str = "r", *args: object, **kwargs: object) -> object:
        nonlocal attempt_count
        real = original_fdopen(fd, mode, *args, **kwargs)
        if "w" in mode:
            attempt_count += 1

            class FailOnWrite:
                def write(self, content: bytes) -> int:
                    err = OSError(errno.ENOSPC, "No space left on device")
                    err.errno = errno.ENOSPC
                    raise err

                def __getattr__(self, name: str) -> object:
                    return getattr(real, name)

                def __enter__(self) -> FailOnWrite:
                    return self

                def __exit__(self, *a: object) -> None:
                    real.close()

            return FailOnWrite()
        return real

    with patch("os.fdopen", side_effect=counting_fdopen):
        with pytest.raises(DiskFullError):
            download_one(http_client, task, retry_policy=FAST_RETRY)

    assert attempt_count == 1, f"phải thử đúng 1 lần, nhưng thử {attempt_count} lần"
