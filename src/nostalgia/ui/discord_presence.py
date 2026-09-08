"""Discord Rich Presence qua IPC cục bộ, KHÔNG thêm thư viện.

Discord đang chạy mở một socket `discord-ipc-N` (Linux/macOS: unix socket trong
$XDG_RUNTIME_DIR, /tmp hoặc thư mục snap/flatpak; Windows: named pipe). Giao thức rất nhỏ:
mỗi khung = opcode (uint32 LE) + độ dài (uint32 LE) + JSON. Bắt tay `{"v":1,"client_id":…}`
rồi `SET_ACTIVITY`. Không có Discord thì `connect` trả False và mọi thứ im lặng — presence là
thứ trang trí, không được làm phiền việc chơi.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import struct
import sys
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
HEADER = struct.Struct("<II")
MAX_FRAME_BYTES = 64 * 1024
SOCKET_TIMEOUT_SECONDS = 2.0


def candidate_socket_paths(
    environ: Mapping[str, str], platform_name: str = sys.platform
) -> list[Path]:
    """Mọi chỗ Discord có thể đặt socket, thử theo thứ tự. Windows dùng named pipe."""
    if platform_name == "win32":
        return [Path(rf"\\?\pipe\discord-ipc-{number}") for number in range(10)]
    socket_dirs: list[Path] = []
    for variable in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP"):
        if environ.get(variable):
            socket_dirs.append(Path(environ[variable]))
    socket_dirs.append(Path("/tmp"))
    runtime_dir = environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        # Discord cài dạng snap / flatpak nằm trong hộp cát riêng.
        socket_dirs.append(Path(runtime_dir) / "snap.discord")
        socket_dirs.append(Path(runtime_dir) / "app" / "com.discordapp.Discord")
    seen: set[Path] = set()
    found: list[Path] = []
    for socket_dir in socket_dirs:
        if socket_dir in seen:
            continue
        seen.add(socket_dir)
        found.extend(socket_dir / f"discord-ipc-{number}" for number in range(10))
    return found


def encode_frame(opcode: int, payload: Mapping[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode()
    return HEADER.pack(opcode, len(body)) + body


def decode_frame(chunk: bytes) -> tuple[int, dict[str, Any]] | None:
    """Một khung trọn vẹn → (opcode, JSON); thiếu byte thì None."""
    if len(chunk) < HEADER.size:
        return None
    opcode, length = HEADER.unpack_from(chunk)
    if length > MAX_FRAME_BYTES or len(chunk) < HEADER.size + length:
        return None
    body = json.loads(chunk[HEADER.size : HEADER.size + length].decode())
    return opcode, body if isinstance(body, dict) else {}


def build_activity(details: str, state: str, started_at: int) -> dict[str, Any]:
    activity: dict[str, Any] = {"details": details[:128], "state": state[:128]}
    if started_at > 0:
        activity["timestamps"] = {"start": started_at}
    return activity


class DiscordPresence:
    """Một kết nối IPC. Dùng từ MỘT luồng; mọi lỗi socket đổi thành `connected == False`."""

    def __init__(
        self, client_id: str, *, environ: Mapping[str, str] | None = None, pid: int | None = None
    ) -> None:
        self._client_id = client_id.strip()
        self._environ = os.environ if environ is None else environ
        self._pid = os.getpid() if pid is None else pid
        self._socket: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> bool:
        if not self._client_id:
            return False
        for path in candidate_socket_paths(self._environ):
            connection = self._open(path)
            if connection is None:
                continue
            try:
                connection.sendall(
                    encode_frame(OP_HANDSHAKE, {"v": 1, "client_id": self._client_id})
                )
                reply = decode_frame(connection.recv(MAX_FRAME_BYTES))
            except OSError:
                connection.close()
                continue
            if reply is None or reply[0] != OP_FRAME or reply[1].get("evt") != "READY":
                connection.close()
                continue
            self._socket = connection
            return True
        return False

    def set_activity(self, details: str, state: str, started_at: int) -> bool:
        return self._send_command(
            "SET_ACTIVITY",
            {"pid": self._pid, "activity": build_activity(details, state, started_at)},
        )

    def clear_activity(self) -> bool:
        return self._send_command("SET_ACTIVITY", {"pid": self._pid})

    def close(self) -> None:
        if self._socket is None:
            return
        with contextlib.suppress(OSError):
            self._socket.sendall(encode_frame(OP_CLOSE, {}))
        self._socket.close()
        self._socket = None

    def _send_command(self, command: str, arguments: Mapping[str, Any]) -> bool:
        if self._socket is None:
            return False
        frame = encode_frame(
            OP_FRAME, {"cmd": command, "args": dict(arguments), "nonce": str(uuid.uuid4())}
        )
        try:
            self._socket.sendall(frame)
            self._socket.recv(MAX_FRAME_BYTES)
        except OSError:
            self.close()
            return False
        return True

    @staticmethod
    def _open(path: Path) -> socket.socket | None:
        if sys.platform == "win32":
            return None  # named pipe của Windows: chưa hỗ trợ, im lặng
        if not path.exists():
            return None
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(SOCKET_TIMEOUT_SECONDS)
        try:
            connection.connect(str(path))
        except OSError:
            connection.close()
            return None
        return connection
