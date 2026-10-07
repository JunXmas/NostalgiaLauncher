"""Paid local server runs: renewable service authorization and graceful world saving."""

from __future__ import annotations

import contextlib
import re
import threading
import time
from pathlib import Path

from nostalgia.errors import NostalgiaError, ServerError, SessionRevoked
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
            self.authorize()
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
            gateway = self._gateway
            if gateway is None:
                raise ServerError("Dịch vụ tài khoản đã ngắt kết nối.")
            lease = gateway.start(server_id)
            self._ready, self._active_run = False, lease.lease_token

            def output(line: str) -> None:
                if self._active_run == lease.lease_token:
                    if re.search(r"Done \([0-9.]+s\)!", line):
                        self._ready = True
                    on_output(line)

            try:
                if gateway is not self._gateway:
                    raise SessionRevoked("Phiên Google đã thay đổi trong lúc khởi chạy server.")
                if cancel_token:
                    cancel_token.raise_if_cancelled()
                if not time.time() < lease.expires_at <= time.time() + 180:
                    raise ServerError("Phiên server không hợp lệ.")
                self._process = start_server(
                    server, self._store.directory(server_id), java_binary, output
                )
                self._lease, self._running_id = lease, server_id
                self._active_port = int(port_text)
                self._monitor_stop = threading.Event()
                threading.Thread(
                    target=self._monitor, args=(self._monitor_stop, on_output), daemon=True
                ).start()
            except BaseException:
                self._active_run = ""
                with contextlib.suppress(NostalgiaError):
                    gateway.release(lease)
                raise

    def _monitor(self, stop_event: threading.Event, on_output: OutputFn) -> None:
        while not stop_event.wait(25):
            with self._lock:
                if stop_event.is_set():
                    return
                try:
                    self.heartbeat()
                except NostalgiaError as error:
                    on_output("[Nostalgia/ERROR] " + str(error))

    def heartbeat(self) -> None:
        with self._lock:
            if not self._lease:
                return
            if not self.running_id:
                self.stop()
                return
            lease = self._lease
            try:
                if self._gateway is None or time.time() >= lease.expires_at:
                    raise ServerError("Phiên host server đã hết hạn.")
                self._lease = self._gateway.renew(lease)
            except NostalgiaError as error:
                # Definitive rejection ends the run; network faults get only the remaining lease.
                if (
                    isinstance(error, (ServerError, SessionRevoked))
                    or time.time() >= lease.expires_at
                ):
                    self.stop()
                raise

    def command(self, text: str) -> None:
        with self._lock:
            if not self._process:
                raise ServerError("Server chưa chạy.")
            self._process.command(text)

    def stop(self) -> None:
        with self._lock:
            self._monitor_stop.set()
            try:
                if self._process:
                    self._process.stop()
            finally:
                lease, gateway = self._lease, self._gateway
                self._lease, self._process, self._running_id = None, None, ""
                self._ready, self._active_run = False, ""
                self._active_port = 0
                if lease and gateway:
                    with contextlib.suppress(NostalgiaError):
                        gateway.release(lease)

    def shutdown(self) -> None:
        self.stop()
        self._http_client.close()

    def room_connection(self) -> ServerConnection:
        with self._lock:
            self.authorize()
            if not self.ready_id or not self._lease or time.time() >= self._lease.expires_at:
                raise ServerError("Server chưa sẵn sàng hoặc phiên host đã hết hạn.")
            server = self.server(self.running_id)
            return ServerConnection(server.server_id, server.display_name, self._active_port)
