"""Context TLS mặc định: một cho cả tiến trình, dùng chung giữa các HttpClient và các luồng.

Trước đây mỗi HttpClient gọi `ssl.create_default_context()`; lúc mở cửa sổ vài cầu nối cùng
dựng client trong luồng nền → nạp chứng chỉ hệ thống song song → CPython segfault trên CI
(run 34344396340). Test này dựng 8 client từ 8 luồng cùng lúc và đòi đúng MỘT context."""

from __future__ import annotations

import ssl
import sys
import threading

import pytest

from nostalgia.net import tls
from nostalgia.net.http import HttpClient
from nostalgia.net.tls import default_tls_context


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


def test_uses_the_os_verifier_when_truststore_is_installed() -> None:
    """Windows cũ thiếu root trong kho: `ssl` chuẩn hỏng TLS với cdn.modrinth.com trong khi
    curl (Schannel) vẫn vào được. Gói phát hành có `truststore` nên phải xác minh qua hệ điều
    hành, và vẫn xác minh đầy đủ (chứng chỉ + tên máy)."""
    truststore = pytest.importorskip("truststore")
    context = tls.system_verifier_context()
    assert isinstance(context, truststore.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname


def test_falls_back_to_stdlib_ssl_without_truststore(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "truststore", None)  # import truststore -> ImportError
    monkeypatch.setattr(tls, "_TLS_CACHE", {})
    assert tls.system_verifier_context() is None
    context = tls.default_tls_context()
    assert type(context) is ssl.SSLContext
    assert context.verify_mode == ssl.CERT_REQUIRED
