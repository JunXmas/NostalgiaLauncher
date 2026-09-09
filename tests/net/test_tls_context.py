"""Context TLS mặc định: một cho cả tiến trình, dùng chung giữa các HttpClient và các luồng.

Trước đây mỗi HttpClient gọi `ssl.create_default_context()`; lúc mở cửa sổ vài cầu nối cùng
dựng client trong luồng nền → nạp chứng chỉ hệ thống song song → CPython segfault trên CI
(run 34344396340). Test này dựng 8 client từ 8 luồng cùng lúc và đòi đúng MỘT context."""

from __future__ import annotations

import ssl
import threading

from nostalgia.net.http import HttpClient, default_tls_context


def test_default_tls_context_is_created_once_and_shared_across_threads() -> None:
    seen: list[ssl.SSLContext] = []
    gate = threading.Barrier(8)

    def build_client() -> None:
        gate.wait()
        seen.append(HttpClient()._tls_context)

    workers = [threading.Thread(target=build_client) for _ in range(8)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert len(seen) == 8
    assert all(context is default_tls_context() for context in seen), "phải là cùng một object"
    assert default_tls_context().verify_mode == ssl.CERT_REQUIRED, "vẫn xác minh chứng chỉ đầy đủ"


def test_an_injected_context_is_kept_for_that_client_only() -> None:
    private = ssl.create_default_context()
    assert HttpClient(tls_context=private)._tls_context is private
    assert HttpClient()._tls_context is not private
