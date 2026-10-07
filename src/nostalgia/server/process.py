"""Safe Java subprocess with stdin console and graceful Minecraft 'stop', no shell scripts."""

from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path

from nostalgia.errors import ServerError
from nostalgia.launch.game_process import GameProcess, OutputFn
from nostalgia.server.model import DedicatedServer
from nostalgia.server.properties import load_properties
from nostalgia.server.store import jar_digest, owned_path
from nostalgia.system.platform_info import resolve_creation_flags


class ServerProcess:
    def __init__(self, process: subprocess.Popen[bytes], on_output: OutputFn) -> None:
        self._raw = process
        self._game = GameProcess(process, on_output)
        self._write_lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._game.is_running

    @property
    def exit_code(self) -> int | None:
        return self._game.exit_code

    def command(self, text: str) -> None:
        if not text.strip() or len(text) > 2048 or any(ord(c) < 32 for c in text):
            raise ServerError("Lệnh console phải nằm trên một dòng, tối đa 2048 ký tự.")
        with self._write_lock:
            if not self.is_running or self._raw.stdin is None:
                raise ServerError("Server chưa chạy.")
            try:
                self._raw.stdin.write((text.strip().lstrip("/") + "\n").encode())
                self._raw.stdin.flush()
            except (OSError, ValueError) as error:
                raise ServerError("Không gửi được lệnh đến server.") from error

    def stop(self, grace_seconds: float = 30.0) -> int:
        if not self.is_running:
            return self._game.wait(timeout=2)
        try:
            self.command("stop")
            return self._game.wait(timeout=grace_seconds)
        except (ServerError, subprocess.TimeoutExpired):
            return self._game.stop(grace_seconds=3)
        finally:
            if self._raw.stdin:
                self._raw.stdin.close()


def start_server(
    server: DedicatedServer, directory: Path, java_binary: Path, on_output: OutputFn
) -> ServerProcess:
    if not load_properties(directory).eula_accepted:
        raise ServerError("Bạn cần đọc và đồng ý Minecraft EULA trước khi chạy server.")
    if not 512 <= server.heap_megabytes <= 32768:
        raise ServerError("RAM server phải nằm trong khoảng 512-32768 MB.")
    jar_path = owned_path(directory, "server.jar")
    if jar_digest(jar_path) != server.jar_sha256:
        raise ServerError("server.jar đã thay đổi. Cài lại server từ bản tải chính thức.")
    argv = [
        str(java_binary),
        "-Xms512M",
        f"-Xmx{server.heap_megabytes}M",
        "-jar",
        "server.jar",
        "nogui",
    ]
    try:
        process = subprocess.Popen(
            argv,
            cwd=directory,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=sys.platform != "win32",
            creationflags=resolve_creation_flags(sys.platform),
        )
    except OSError as error:
        raise ServerError("Không khởi chạy được Java cho server.") from error
    return ServerProcess(process, on_output)
