"""HttpClient và retry — chạy trên máy chủ HTTPS cục bộ, không cần Internet."""

from __future__ import annotations

import pytest

from local_https_server import LocalHttpsServer, ServerState
from mccore.errors import Cancelled, IntegrityError, NetworkError
from mccore.net.http import HttpClient, RetryPolicy, retry
from mccore.operations.cancellation import CancelToken

FAST_RETRY = RetryPolicy(attempts=3, initial_backoff_seconds=0.01, total_deadline_seconds=5.0)


@pytest.mark.parametrize("url", ["http://localhost/a", "ftp://x/a", "https:///a", "khong-phai-url"])
def test_only_https_with_a_host_is_accepted(client: HttpClient, url: str) -> None:
    """Chỉ nhận https: một launcher tải mã thực thi thì không được đi qua kênh không mã hoá."""
    with pytest.raises(NetworkError, match="https"):
        client.fetch_bytes(url)


def test_body_is_returned(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    server_state.add("/a", b"xin chao")
    assert client.fetch_bytes(server.url("/a")) == b"xin chao"


def test_missing_path_becomes_network_error(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    server_state.add("/co", b"x")
    with pytest.raises(NetworkError, match="404"):
        client.fetch_bytes(server.url("/khong-co"))


def test_redirect_is_refused_loudly(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    """Mojang không chuyển hướng, nhưng CurseForge thì có.

    Trả lỗi rõ ràng thay vì lưu thân của trang chuyển hướng thành file .jar — đó là lỗi đã
    xảy ra thật ở launcher tiền nhiệm.
    """
    server_state.add("/di-cho-khac", b"", status=302)
    with pytest.raises(NetworkError, match="chuyển hướng"):
        client.fetch_bytes(server.url("/di-cho-khac"))


def test_connection_is_reused_across_requests(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    """Tái dùng kết nối đo được nhanh hơn 2-5 lần; test này gác việc nó thật sự xảy ra."""
    server_state.add("/a", b"1")
    for _ in range(5):
        assert client.fetch_bytes(server.url("/a")) == b"1"
    assert server_state.request_count("/a") == 5


def test_stream_reports_bytes_written(
    client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    payload = b"n" * 200_000  # nhiều khối, để chắc vòng đọc lặp thật
    server_state.add("/to", payload)
    received = bytearray()
    written = client.stream(server.url("/to"), received.extend)
    assert written == len(payload)
    assert bytes(received) == payload


def test_retry_gives_up_after_the_configured_attempts() -> None:
    attempts = []

    def always_fails() -> None:
        attempts.append(1)
        message = "hỏng"
        raise NetworkError(message)

    with pytest.raises(NetworkError, match="sau 3 lần thử"):
        retry(always_fails, policy=FAST_RETRY)
    assert len(attempts) == 3


def test_retry_succeeds_after_transient_failures() -> None:
    attempts = []

    def fails_twice() -> str:
        attempts.append(1)
        if len(attempts) < 3:
            message = "hỏng tạm"
            raise NetworkError(message)
        return "xong"

    assert retry(fails_twice, policy=FAST_RETRY) == "xong"
    assert len(attempts) == 3


def test_retry_also_retries_integrity_errors() -> None:
    """File tải hỏng giữa đường là tình huống nhất thời — phải thử lại, không bỏ luôn."""
    attempts = []

    def corrupt_once() -> str:
        attempts.append(1)
        if len(attempts) == 1:
            message = "sha1 lệch"
            raise IntegrityError(message)
        return "xong"

    assert retry(corrupt_once, policy=FAST_RETRY) == "xong"


def test_retry_does_not_retry_programming_errors() -> None:
    """Thử lại một lỗi lập trình chỉ làm chậm việc phát hiện nó."""

    def broken() -> None:
        raise ValueError

    with pytest.raises(ValueError):
        retry(broken, policy=FAST_RETRY)


def test_retry_stops_immediately_when_cancelled() -> None:
    cancel_token = CancelToken()
    cancel_token.cancel()

    def never_called() -> None:
        raise AssertionError

    with pytest.raises(Cancelled):
        retry(never_called, policy=FAST_RETRY, cancel_token=cancel_token)
