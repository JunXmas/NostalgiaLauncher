"""Máy chủ HTTPS cục bộ cho test tải file — không cần Internet.

Vì sao HTTPS thật chứ không phải HTTP: `HttpClient` chỉ nhận `https`, và ta muốn test đi
đúng đường mà người dùng đi, kể cả phần bắt tay TLS. Chứng chỉ tự ký dựng bằng `openssl`
một lần cho cả phiên test.
"""

from __future__ import annotations

import http.server
import shutil
import ssl
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Route:
    """Một đường dẫn và cách máy chủ trả lời nó.

    `fail_first` cho phép dựng tình huống "CDN lỗi vài lần rồi mới được" — thứ xảy ra thật
    và là lý do bộ tải phải có retry.
    """

    body: bytes
    status: int = 200
    fail_first: int = 0
    requests: int = 0
    failures_served: int = 0


@dataclass
class ServerState:
    routes: dict[str, Route] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, path: str, body: bytes, *, status: int = 200, fail_first: int = 0) -> str:
        with self.lock:
            self.routes[path] = Route(body=body, status=status, fail_first=fail_first)
        return path

    def request_count(self, path: str) -> int:
        with self.lock:
            return self.routes[path].requests


def make_certificate(directory: Path) -> tuple[Path, Path]:
    """Dựng chứng chỉ tự ký cho `localhost`. Trả về (cert, key)."""
    certificate = directory / "cert.pem"
    key = directory / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(certificate),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost,IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )
    return certificate, key


def openssl_available() -> bool:
    return shutil.which("openssl") is not None


class LocalHttpsServer:
    """Máy chủ chạy trong luồng riêng, tự dừng khi ra khỏi khối `with`."""

    def __init__(self, state: ServerState, certificate: Path, key: Path) -> None:
        self._state = state
        handler = _make_handler(state)
        self._server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate, key)
        self._server.socket = context.wrap_socket(self._server.socket, server_side=True)
        # poll_interval nhỏ: mặc định 0,5 s là khoảng thời gian `shutdown()` phải chờ, và
        # với hơn 30 test thì riêng việc dừng máy chủ đã tốn 15 giây. Đo được: 504 ms mỗi
        # lần dựng+dừng, sau khi sửa còn dưới 20 ms.
        self._thread = threading.Thread(
            target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )

    def __enter__(self) -> LocalHttpsServer:
        self._thread.start()
        return self

    def __exit__(self, *_exception: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def url(self, path: str) -> str:
        return f"https://localhost:{self._server.server_address[1]}{path}"


def _make_handler(state: ServerState) -> type[http.server.BaseHTTPRequestHandler]:
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            with state.lock:
                route = state.routes.get(self.path)
                if route is None:
                    self.send_error(404)
                    return
                route.requests += 1
                if route.failures_served < route.fail_first:
                    route.failures_served += 1
                    self.send_error(503)
                    return
                body, status = route.body, route.status
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            """Im lặng: log của máy chủ test chỉ làm rối kết quả pytest."""

    return Handler
