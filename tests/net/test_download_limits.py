"""Ba lỗ hổng đã đo được rồi vá — test ở đây để chúng không quay lại.

Cả ba đều là chuyện tài nguyên: máy chủ gửi quá nhiều, nút dừng không dừng được, và URL
chứa tên đăng nhập. Không cái nào bị `ruff` hay `mypy` phát hiện; chỉ có đo mới thấy.
"""

from __future__ import annotations

import ssl
import threading
import time
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nostalgia.errors import Cancelled, NetworkError
from nostalgia.model.download import DownloadTask
from nostalgia.net.download import download_all, download_one
from nostalgia.net.http import HttpClient, RetryPolicy
from nostalgia.operations.cancellation import CancelToken

ONE_ATTEMPT = RetryPolicy(attempts=1, initial_backoff_seconds=0.01, total_deadline_seconds=10.0)
BIG_BODY = b"z" * 400_000


def test_truncation_by_a_lying_server_is_caught_by_sha1(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Máy chủ công bố ÍT hơn nó gửi: `http.client` cắt ở số đã công bố, nên ta nhận một
    file bị hụt mà kích thước vẫn "khớp". Chỉ sha1 bắt được — đó là lý do luật 5 bắt băm
    ngay trong lúc tải chứ không phải băm lại sau."""
    server_state.add("/noi-doi-it", BIG_BODY, declare_length=100)
    task = DownloadTask(
        url=server.url("/noi-doi-it"),
        destination=tmp_path / "a.bin",
        sha1="0" * 40,
        size=100,
    )
    with pytest.raises(Exception, match="sha1"):
        download_one(http_client, task, retry_policy=ONE_ATTEMPT)
    assert list(tmp_path.iterdir()) == [], "không được để lại file tạm"


def test_server_declaring_more_than_it_sends_is_an_error(
    certificate_pair: tuple[Path, Path],
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
) -> None:
    """Chiều ngược lại: công bố NHIỀU hơn gửi. Phải thành lỗi, không thành file hụt.

    Dùng http_client timeout RẤT ngắn: một máy chủ giao thiếu sẽ khiến ta chờ hết timeout ổ cắm,
    và đó chính là lý do `RetryPolicy` phải có `total_deadline_seconds` — bốn lần thử với
    timeout 30 giây là hai phút cho một file.
    """
    certificate, _key = certificate_pair
    impatient = HttpClient(
        timeout_seconds=0.3, tls_context=ssl.create_default_context(cafile=str(certificate))
    )
    server_state.add("/noi-doi-nhieu", b"z" * 100, declare_length=400_000)
    task = DownloadTask(
        url=server.url("/noi-doi-nhieu"), destination=tmp_path / "b.bin", size=400_000
    )
    try:
        with pytest.raises(NetworkError):
            download_one(impatient, task, retry_policy=ONE_ATTEMPT)
    finally:
        impatient.close()
    assert list(tmp_path.iterdir()) == []


def test_fetch_bytes_has_a_ceiling(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    """Nạp trọn vào bộ nhớ thì luôn phải có trần, kể cả khi máy chủ tử tế."""
    server_state.add("/to", BIG_BODY)
    with pytest.raises(NetworkError, match="hơn 1000 byte"):
        http_client.fetch_bytes(server.url("/to"), max_bytes=1000)


def test_cancelling_mid_download_stops_quickly(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState, tmp_path: Path
) -> None:
    """Trước khi vá, huỷ giữa lúc tải KHÔNG dừng được file nào: vòng đọc không kiểm cờ.

    Với bản cài 649 MB thì đó là nút dừng vô dụng — đúng lỗi launcher tiền nhiệm từng có.
    """
    tasks = []
    for index in range(4):
        server_state.add(f"/cham{index}", BIG_BODY, chunk_delay_seconds=0.01)
        tasks.append(
            DownloadTask(
                url=server.url(f"/cham{index}"),
                destination=tmp_path / f"f{index}.bin",
                size=len(BIG_BODY),
            )
        )

    cancel_token = CancelToken()
    threading.Timer(0.2, cancel_token.cancel).start()
    started = time.perf_counter()
    with pytest.raises(Cancelled):
        download_all(
            http_client, tasks, workers=4, retry_policy=ONE_ATTEMPT, cancel_token=cancel_token
        )
    elapsed = time.perf_counter() - started
    assert elapsed < 3.0, f"dừng quá chậm: {elapsed:.2f}s"
    assert not any(path.suffix == ".bin" for path in tmp_path.iterdir())


@pytest.mark.parametrize(
    "url",
    [
        "https://ai-do:mat-khau@localhost/x",
        "https://nguoi-dung@localhost/x",
    ],
)
def test_urls_with_credentials_are_refused(http_client: HttpClient, url: str) -> None:
    """`https://ai-do:mat-khau@host/` là mẫu lừa đảo kinh điển: mắt người đọc phần trước
    dấu @ tưởng là tên máy. Trước khi vá, nó chỉ hỏng ở tầng DNS với thông điệp vô nghĩa."""
    with pytest.raises(NetworkError, match="tên đăng nhập"):
        http_client.fetch_bytes(url)


def test_missing_content_length_still_has_a_ceiling(
    http_client: HttpClient, server: LocalHttpsServer, server_state: ServerState
) -> None:
    """Máy chủ không công bố gì cả: trần vẫn phải áp, nếu không thì không có gì chặn."""
    server_state.add("/khong-cong-bo", BIG_BODY, declare_length=-1)
    with pytest.raises(NetworkError, match="hơn 5000 byte"):
        http_client.fetch_bytes(server.url("/khong-cong-bo"), max_bytes=5000)
