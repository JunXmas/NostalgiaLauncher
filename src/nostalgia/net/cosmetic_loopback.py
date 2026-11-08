"""IPC chỉ đọc diện mạo trên loopback; không có API mua, ví hoặc thực thi lệnh."""

import hmac
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer


@dataclass(frozen=True, slots=True)
class CosmeticBootstrap:
    port: int
    nonce: str


class CosmeticLoopback:
    def __init__(self, read: Callable[[], bytes]) -> None:
        nonce = secrets.token_hex(32)

        class Handler(BaseHTTPRequestHandler):
            def setup(self) -> None:
                super().setup()
                self.connection.settimeout(2)

            def do_GET(self) -> None:
                if self.headers.get("Origin") or not hmac.compare_digest(
                    self.path, "/cosmetic/" + nonce
                ):
                    self.send_error(403)
                    return
                payload = read()
                if len(payload) > 16384:
                    self.send_error(503)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                # Không log đường dẫn có nonce hoặc body chứa capability.
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._server.timeout = 2
        self.bootstrap = CosmeticBootstrap(self._server.server_port, nonce)
        self._thread = threading.Thread(
            target=lambda: self._server.serve_forever(poll_interval=0.1),
            name="nostalgia-cosmetic-ipc",
            daemon=True,
        )
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
