"""Discord Rich Presence qua IPC cục bộ, KHÔNG thêm thư viện.

Discord đang chạy mở một socket `discord-ipc-N` (Linux/macOS: unix socket trong
$XDG_RUNTIME_DIR, /tmp hoặc thư mục snap/flatpak; Windows: named pipe, mở được như file
thường bằng `open()`). Giao thức rất nhỏ: mỗi khung = opcode (uint32 LE) + độ dài (uint32 LE)
+ JSON. Bắt tay `{"v":1,"client_id":…}` rồi `SET_ACTIVITY`. Không có Discord thì `connect`
trả False và mọi thứ im lặng — presence là thứ trang trí, không được làm phiền việc chơi.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import struct
import sys
import uuid
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, BinaryIO, Protocol

OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
HEADER = struct.Struct("<II")
MAX_FRAME_BYTES = 64 * 1024
SOCKET_TIMEOUT_SECONDS = 2.0


class Connection(Protocol):
    """Socket Unix và named pipe Windows dùng chung giao diện này."""

    def sendall(self, payload: bytes) -> None: ...
    def recv(self, size: int) -> bytes: ...
    def close(self) -> None: ...


def candidate_socket_paths(
    environ: Mapping[str, str], platform_name: str = sys.platform
) -> list[Path]:
    """Mọi chỗ Discord có thể đặt socket, thử theo thứ tự. Windows dùng named pipe."""
    if platform_name == "win32":
        return [Path(rf"\\.\pipe\discord-ipc-{number}") for number in range(10)]
    socket_dirs: list[Path] = []
    for variable in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP"):
        if environ.get(variable):
            socket_dirs.append(Path(environ[variable]))
    if not environ.get("XDG_RUNTIME_DIR") and hasattr(os, "getuid"):
        # Snap/Flatpak/nhiều distro không đặt XDG_RUNTIME_DIR trong môi trường được truyền
        # vào (vd chạy từ systemd service) nhưng thư mục chuẩn theo UID vẫn tồn tại.
        socket_dirs.append(Path(f"/run/user/{os.getuid()}"))
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


def read_frame(recv: Callable[[int], bytes]) -> tuple[int, dict[str, Any]] | None:
    """Đọc một khung trọn vẹn, gọi `recv` nhiều lần nếu khung tới phân mảnh (thường ở TCP,
    nhưng cũng có thể xảy ra với named pipe). `recv` rỗng giữa chừng nghĩa là đầu kia đóng."""
    buffer = b""
    while len(buffer) < HEADER.size:
        chunk = recv(HEADER.size - len(buffer))
        if not chunk:
            return None
        buffer += chunk
    _, length = HEADER.unpack_from(buffer)
    if length > MAX_FRAME_BYTES:
        return None
    while len(buffer) < HEADER.size + length:
        chunk = recv(HEADER.size + length - len(buffer))
        if not chunk:
            return None
        buffer += chunk
    return decode_frame(buffer)


def build_activity(details: str, state: str, started_at: int) -> dict[str, Any]:
    activity: dict[str, Any] = {"details": details[:128], "state": state[:128]}
    if started_at > 0:
        activity["timestamps"] = {"start": started_at}
    return activity


class _PipeConnection:
    """Bọc named pipe Windows (mở như file thường) sau cùng giao diện `Connection` với socket
    Unix, để phần còn lại của module không cần biết đang chạy trên hệ nào."""

    def __init__(self, handle: BinaryIO) -> None:
        self._handle = handle

    def sendall(self, payload: bytes) -> None:
        self._handle.write(payload)
        self._handle.flush()

    def recv(self, size: int) -> bytes:
        return self._handle.read(size)

    def close(self) -> None:
        self._handle.close()


def _open_pipe(path: Path) -> BinaryIO:
    return path.open("r+b", buffering=0)


class DiscordPresence:
    """Một kết nối IPC. Dùng từ MỘT luồng; mọi lỗi socket đổi thành `connected == False`."""

    def __init__(
        self,
        client_id: str,
        *,
        environ: Mapping[str, str] | None = None,
        pid: int | None = None,
        platform_name: str = sys.platform,
        pipe_opener: Callable[[Path], BinaryIO] = _open_pipe,
    ) -> None:
        self._client_id = client_id.strip()
        self._environ = os.environ if environ is None else environ
        self._pid = os.getpid() if pid is None else pid
        self._platform_name = platform_name
        self._pipe_opener = pipe_opener
        self._socket: Connection | None = None

    @property
    def connected(self) -> bool:
        return self._socket is not None

    def connect(self) -> bool:
        if not self._client_id:
            return False
        for path in candidate_socket_paths(self._environ, self._platform_name):
            connection = self._open(path)
            if connection is None:
                continue
            try:
                connection.sendall(
                    encode_frame(OP_HANDSHAKE, {"v": 1, "client_id": self._client_id})
                )
                reply = read_frame(connection.recv)
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
            reply = read_frame(self._socket.recv)
        except OSError:
            self.close()
            return False
        if reply is None:
            self.close()
            return False
        return reply[1].get("evt") != "ERROR"

    def _open(self, path: Path) -> Connection | None:
        if self._platform_name == "win32":
            try:
                return _PipeConnection(self._pipe_opener(path))
            except OSError:
                return None
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
