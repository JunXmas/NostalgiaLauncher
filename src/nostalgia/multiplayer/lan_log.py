"""Đọc tăng dần latest.log của đúng bản chơi; bỏ thông báo LAN từ lần chạy trước."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from nostalgia.multiplayer.lan_output import lan_port_from_output

READ_LIMIT = 64 * 1024


class LanLogReader:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._identity: tuple[int, int] | None = None
        self._offset = 0
        self._modified = 0
        self._pending = b""
        try:
            status = path.stat()
            self._identity = status.st_dev, status.st_ino
            self._offset, self._modified = status.st_size, status.st_mtime_ns
        except OSError:
            pass

    def read_port(self) -> int:
        """Đọc tối đa 64 KiB/lần, giữ dòng chưa đủ, chỉ trả cổng trong phần log mới."""
        try:
            if not stat.S_ISREG(self._path.stat().st_mode):
                return 0
            with self._path.open("rb") as stream:
                status = os.fstat(stream.fileno())
                if not stat.S_ISREG(status.st_mode):
                    return 0
                identity = status.st_dev, status.st_ino
                if (
                    identity != self._identity
                    or status.st_size < self._offset
                    or (status.st_size == self._offset and status.st_mtime_ns != self._modified)
                ):
                    self._offset, self._pending = 0, b""
                if status.st_size - self._offset > READ_LIMIT:
                    self._offset, self._pending = status.st_size - READ_LIMIT, b""
                    stream.seek(self._offset)
                    stream.readline(READ_LIMIT)
                else:
                    stream.seek(self._offset)
                content = stream.read(READ_LIMIT)
                self._offset = stream.tell()
                self._identity, self._modified = identity, status.st_mtime_ns
        except OSError:
            return 0
        lines = (self._pending + content).split(b"\n")
        self._pending = lines.pop()[-READ_LIMIT:]
        port = 0
        for line in lines:
            port = lan_port_from_output(line.decode("utf-8", errors="replace")) or port
        return port
