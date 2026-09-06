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
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Route:
    """Một đường dẫn và cách máy chủ trả lời nó.

    `fail_first` dựng tình huống "CDN lỗi vài lần rồi mới được" — xảy ra thật, và là lý do
    bộ tải phải có retry.

    `declare_length` cho phép nói dối: gửi nhiều hơn `Content-Length` đã công bố, hoặc không
    công bố gì cả. Cần để kiểm cái trần kích thước — không có trần thì một máy chủ như vậy
    khiến ta ghi tới khi hết đĩa.

    `chunk_delay_seconds` làm máy chủ nhỏ giọt, để kiểm việc huỷ giữa lúc đang tải.
    """

    body: bytes
    status: int = 200
    fail_first: int = 0
    declare_length: int | None = None
    chunk_delay_seconds: float = 0.0
    requests: int = 0
    failures_served: int = 0
    # Những gì máy chủ NHẬN ĐƯỢC ở lần gọi gần nhất. Cần để kiểm phía gửi: một luồng đăng
    # nhập sai một trường trong thân request sẽ hỏng theo cách chỉ máy chủ thật mới thấy.
    received_body: bytes = b""
    received_headers: dict[str, str] = field(default_factory=dict)
    # Đường dẫn đầy đủ kèm chuỗi truy vấn: route khớp theo phần trước dấu `?`, nhưng test
    # tìm kiếm cần đọc được tham số đã gửi.
    received_path: str = ""


@dataclass
class ServerState:
    routes: dict[str, Route] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add(
        self,
        path: str,
        body: bytes,
        *,
        status: int = 200,
        fail_first: int = 0,
        declare_length: int | None = None,
        chunk_delay_seconds: float = 0.0,
    ) -> str:
        with self.lock:
            self.routes[path] = Route(
                body=body,
                status=status,
                fail_first=fail_first,
                declare_length=declare_length,
                chunk_delay_seconds=chunk_delay_seconds,
            )
        return path

    def request_count(self, path: str) -> int:
        with self.lock:
            return self.routes[path].requests

    def received_body(self, path: str) -> bytes:
        """Thân request mà máy chủ nhận được ở lần gọi gần nhất."""
        with self.lock:
            return self.routes[path].received_body

    def received_path(self, path: str) -> str:
        """Đường dẫn kèm chuỗi truy vấn của lần gọi gần nhất."""
        with self.lock:
            return self.routes[path].received_path

    def received_header(self, path: str, name: str) -> str:
        with self.lock:
            return self.routes[path].received_headers.get(name, "")


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


class _QuietServer(http.server.ThreadingHTTPServer):
    """Không in traceback: phía kia ngắt giữa lúc gửi là điều nhiều test CỐ Ý gây ra."""

    def handle_error(self, *_args: object) -> None:
        return


class LocalHttpsServer:
    """Máy chủ chạy trong luồng riêng, tự dừng khi ra khỏi khối `with`."""

    def __init__(self, state: ServerState, certificate: Path, key: Path) -> None:
        self._state = state
        handler = _make_handler(state)
        self._server = _QuietServer(("127.0.0.1", 0), handler)
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

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            self._received = self.rfile.read(length) if length else b""
            self.do_GET()

        def do_GET(self) -> None:
            with state.lock:
                route = state.routes.get(self.path.split("?", 1)[0])
                if route is not None:
                    # Ghi lại cho MỌI phương thức: header `Authorization` đi kèm GET, còn
                    # thân đi kèm POST — kiểm phía gửi cần cả hai.
                    route.received_body = getattr(self, "_received", b"")
                    route.received_headers = dict(self.headers)
                    route.received_path = self.path
                if route is None:
                    self.send_error(404)
                    return
                route.requests += 1
                if route.failures_served < route.fail_first:
                    route.failures_served += 1
                    self.send_error(503)
                    return
                body, status = route.body, route.status
                declared = route.declare_length
                delay = route.chunk_delay_seconds
            self.send_response(status)
            if declared is None:
                self.send_header("Content-Length", str(len(body)))
            elif declared >= 0:
                self.send_header("Content-Length", str(declared))
            self.end_headers()
            if delay <= 0:
                self.wfile.write(body)
                return
            for start in range(0, len(body), 16384):
                try:
                    self.wfile.write(body[start : start + 16384])
                    self.wfile.flush()
                except OSError:
                    return  # phía kia đã ngắt: đúng điều test mong đợi
                time.sleep(delay)

        def log_message(self, *_args: object) -> None:
            """Im lặng: log của máy chủ test chỉ làm rối kết quả pytest."""

    return Handler
