"""Discord Rich Presence trên Windows: giao thức giống Linux, nhưng truyền tải là named pipe
(`open()`/`read()`/`write()`) thay vì unix socket. Tách khỏi test_discord_presence.py vì đây
là bề mặt riêng (pipe_opener) không đụng tới FakeDiscord/socket thật."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, cast

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from nostalgia.ui.discord_presence import (
    OP_FRAME,
    OP_HANDSHAKE,
    DiscordPresence,
    decode_frame,
    encode_frame,
)

pytestmark = pytest.mark.usefixtures("qt_app")


class FakeWindowsPipe:
    """Named pipe Windows giả: `write` ghi lại khung gửi, `read` trả khung phản hồi lập trình
    sẵn — cắt nhỏ theo `fragment_size` để buộc `read_frame` gọi `read()` nhiều lần cho một
    khung, đúng như named pipe thật có thể trả về ít byte hơn yêu cầu."""

    def __init__(self, replies: list[bytes], fragment_size: int = 4) -> None:
        self._replies = list(replies)
        self._pending = b""
        self.written: list[bytes] = []
        self._fragment_size = fragment_size

    def write(self, payload: bytes) -> int:
        self.written.append(payload)
        if self._replies:
            self._pending += self._replies.pop(0)
        return len(payload)

    def flush(self) -> None:
        pass

    def read(self, size: int) -> bytes:
        chunk = self._pending[: min(size, self._fragment_size)]
        self._pending = self._pending[len(chunk) :]
        return chunk

    def close(self) -> None:
        pass


def test_windows_named_pipe_handshake_and_activity() -> None:
    ready = encode_frame(OP_FRAME, {"cmd": "DISPATCH", "evt": "READY"})
    ack = encode_frame(OP_FRAME, {"cmd": "SET_ACTIVITY", "evt": None})
    pipe = FakeWindowsPipe([ready, ack])
    presence = DiscordPresence(
        "123456789",
        environ={},
        platform_name="win32",
        pipe_opener=lambda _path: cast(BinaryIO, pipe),
    )
    assert presence.connect() is True
    assert presence.set_activity("Đang chơi Sinh tồn", "Nostalgia Launcher", 0) is True
    assert decode_frame(pipe.written[0]) == (
        OP_HANDSHAKE,
        {"v": 1, "client_id": "123456789"},
    )
    activity = decode_frame(pipe.written[1])
    assert activity is not None and activity[1]["cmd"] == "SET_ACTIVITY"


def test_windows_named_pipe_missing_discord_stays_quiet() -> None:
    def missing(_path: Path) -> BinaryIO:
        raise OSError("no such pipe")

    presence = DiscordPresence("123", environ={}, platform_name="win32", pipe_opener=missing)
    assert presence.connect() is False
