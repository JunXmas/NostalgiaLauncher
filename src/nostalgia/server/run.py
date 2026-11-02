"""Server chạy trên máy người dùng, miễn phí: khởi chạy, console và dừng có lưu thế giới."""

from __future__ import annotations

import re
from pathlib import Path

from nostalgia.errors import ServerError
from nostalgia.java.mojang_jre import ensure_java_runtime
from nostalgia.launch.game_process import OutputFn
from nostalgia.operations.cancellation import CancelToken
from nostalgia.server.context import ServerContext
from nostalgia.server.model import ServerConnection
from nostalgia.server.process import start_server
from nostalgia.server.properties import load_properties


class ServerRun(ServerContext):
    def start(
        self, server_id: str, on_output: OutputFn, cancel_token: CancelToken | None = None
    ) -> None:
        with self._lock:
            if self.running_id:
                raise ServerError("Dừng server đang chạy trước khi mở server khác.")
            self.stop()
            server = self.server(server_id)
            properties = load_properties(self._store.directory(server_id))
            if not properties.eula_accepted:
                raise ServerError("Bạn cần đồng ý Minecraft EULA và lưu cấu hình trước khi chạy.")
            port_text = dict(properties.values)["server-port"]
            if not port_text.isdigit() or not 1024 <= int(port_text) <= 65535:
                raise ServerError("Cổng server phải nằm trong 1024-65535.")
            if server.java_binary:
                java_binary = Path(server.java_binary)
                if not java_binary.is_file():
                    raise ServerError("Không tìm thấy Java đã chọn.")
            else:
                metadata = self._repository.sync_version_meta(
                    server.game_version, cancel_token=cancel_token
                )
                java_binary = ensure_java_runtime(
                    self._http_client,
                    self.paths,
                    metadata,
                    self.platform,
                    cancel_token=cancel_token,
                ).java_binary
            if cancel_token:
                cancel_token.raise_if_cancelled()
            self._ready = False

            def output(line: str) -> None:
                if re.search(r"Done \([0-9.]+s\)!", line):
                    self._ready = True
                on_output(line)

            self._process = start_server(
                server, self._store.directory(server_id), java_binary, output
            )
            self._running_id = server_id
            self._active_port = int(port_text)

    def command(self, text: str) -> None:
        with self._lock:
            if not self._process:
                raise ServerError("Server chưa chạy.")
            self._process.command(text)

    def stop(self) -> None:
        with self._lock:
            try:
                if self._process:
                    self._process.stop()
            finally:
                self._process, self._running_id = None, ""
                self._ready, self._active_port = False, 0

    def shutdown(self) -> None:
        self.stop()
        self._http_client.close()

    def room_connection(self) -> ServerConnection:
        with self._lock:
            if not self.ready_id:
                raise ServerError("Server chưa sẵn sàng.")
            server = self.server(self.running_id)
            return ServerConnection(server.server_id, server.display_name, self._active_port)
