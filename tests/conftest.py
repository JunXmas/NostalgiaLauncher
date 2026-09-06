"""Cấu hình chung cho test.

Luật số một của kho: đường dẫn không bao giờ được dẫn xuất từ thư mục home. Một fixture chỉ
*chuyển hướng* home sang thư mục tạm là chưa đủ — code vi phạm luật vẫn chạy trơn tru, ghi
vào home giả, và không ai biết. Lưới ở đây vì thế làm hai việc:

1. Đặt lại mọi biến môi trường đường dẫn về thư mục tạm (phòng thân, và cần cho Windows).
2. **Cấm** `Path.home()` và `os.path.expanduser` — gọi tới là rớt ngay tại dòng gây lỗi.

Test nào thật sự cần home thì đánh `@pytest.mark.allow_home`.
"""

from __future__ import annotations

import os
import socket
import ssl
from collections.abc import Iterator
from pathlib import Path

import pytest

from local_https_server import (
    LocalHttpsServer,
    ServerState,
    make_certificate,
    openssl_available,
)
from nostalgia.net.http import HttpClient

# Mọi biến môi trường có thể dẫn code về dữ liệu thật của người dùng.
PATH_ENV_VARS = (
    "HOME",
    "USERPROFILE",
    "HOMEDRIVE",
    "HOMEPATH",
    "APPDATA",
    "LOCALAPPDATA",
    "XDG_DATA_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
)


@pytest.fixture(autouse=True)
def isolated_home(
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Path:
    """Ép mọi đường dẫn vào thư mục tạm, và cấm mọi lối đi vòng qua home.

    Dùng `tmp_path_factory` chứ không phải `tmp_path`: nếu tạo home giả ngay trong `tmp_path`
    thì mọi test liệt kê nội dung `tmp_path` sẽ thấy thêm một thư mục lạ. Đã trả giá một lần.
    """
    home = tmp_path_factory.mktemp("home")

    for name in PATH_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    # Xoá cả biến của chính dự án, kể cả biến thêm về sau.
    for name in [n for n in os.environ if n.startswith("NOSTALGIA_")]:
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows không bao giờ tra HOME
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / ".cache"))
    monkeypatch.setenv("NOSTALGIA_DATA_DIR", str(home / "data"))

    if request.node.get_closest_marker("allow_home") is None:
        message = (
            "Code trong nostalgia không được gọi Path.home() hay expanduser(). "
            "Đường dẫn phải đến từ DataPaths được truyền vào — xem GLOSSARY.md §1.4."
        )

        def forbidden(*_args: object, **_kwargs: object) -> Path:
            raise AssertionError(message)

        monkeypatch.setattr(Path, "home", staticmethod(forbidden))
        monkeypatch.setattr(os.path, "expanduser", forbidden)

    return home


@pytest.fixture(autouse=True)
def no_accidental_internet(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Chặn mọi kết nối ra ngoài máy, trừ test có đánh dấu `network`.

    Không có lưới này thì một test lỡ gọi ra Internet sẽ **treo** thay vì rớt: đã trả giá
    đúng một lần — `account add-microsoft` sau khi có mã ứng dụng mặc định đã gọi thật lên
    Microsoft rồi ngồi chờ người nhập mã suốt 900 giây, và cả bộ test đứng im ở 12%.

    Chặn ở tầng socket chứ không ở tầng `HttpClient`: mọi đường ra Internet đều phải đi qua
    đây, kể cả đường mà một ngày nào đó ai đó viết mới mà quên mất luật này.
    """
    if request.node.get_closest_marker("network") is not None:
        return

    real_connect = socket.socket.connect

    def guarded_connect(self: socket.socket, address: object) -> None:
        host = address[0] if isinstance(address, tuple) else ""
        if host in {"127.0.0.1", "::1", "localhost"}:
            real_connect(self, address)
            return
        message = (
            f"test không đánh dấu `network` nhưng đang gọi ra {address!r}. "
            "Dùng máy chủ cục bộ trong tests/, hoặc đánh dấu @pytest.mark.network."
        )
        raise AssertionError(message)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


@pytest.fixture(scope="session")
def certificate_pair(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    if not openssl_available():
        pytest.skip("cần openssl để dựng chứng chỉ tự ký cho máy chủ test")
    return make_certificate(tmp_path_factory.mktemp("tls"))


@pytest.fixture
def server_state() -> ServerState:
    return ServerState()


@pytest.fixture
def server(
    server_state: ServerState, certificate_pair: tuple[Path, Path]
) -> Iterator[LocalHttpsServer]:
    certificate, key = certificate_pair
    with LocalHttpsServer(server_state, certificate, key) as running:
        yield running


@pytest.fixture
def http_client(certificate_pair: tuple[Path, Path]) -> Iterator[HttpClient]:
    certificate, _key = certificate_pair
    trusting = ssl.create_default_context(cafile=str(certificate))
    http_client = HttpClient(timeout_seconds=5.0, tls_context=trusting)
    try:
        yield http_client
    finally:
        http_client.close()


@pytest.fixture(scope="session")
def qt_app() -> object:
    """Một `QGuiApplication` cho cả phiên — Qt không cho tạo hai. Chỉ test trong `tests/ui/`
    dùng; PySide6 là phụ thuộc tuỳ chọn nên import lười và bỏ qua nếu thiếu."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication(["test"])
