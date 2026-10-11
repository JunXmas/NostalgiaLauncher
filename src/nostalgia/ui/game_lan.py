"""Chỉ gửi cổng LAN qua Qt; stdout và log cùng theo dõi đúng phiên chơi đang chạy."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from nostalgia.api import LanLogReader, lan_port_from_output


class GameLanFeed(QObject):
    lanOpened = Signal(str, int)
    _portArrived = Signal(str, int, int)

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.instance_id = ""
        self.port = 0
        self._generation = 0
        self._lock = threading.Lock()
        self._log_stop = threading.Event()
        self._log_follow: Callable[[], None] | None = None
        self._portArrived.connect(self._apply_port)
        self.destroyed.connect(lambda: self._log_stop.set())

    def receiver(
        self,
        instance_id: str,
        log_receive: Callable[[str], None],
        log_path: Path | None = None,
    ) -> Callable[[str], None]:
        with self._lock:
            self._log_stop.set()
            self._log_stop = stop = threading.Event()
            self._log_follow = None
            self._generation += 1
            generation = self._generation
        if log_path is not None:
            reader = LanLogReader(log_path)

            def follow_log() -> None:
                while not stop.wait(0.5):
                    port = reader.read_port()
                    if port and not stop.is_set():
                        try:
                            self._portArrived.emit(instance_id, port, generation)
                        except RuntimeError:
                            # Cửa sổ đã bị hủy trước khi tín hiệu từ luồng log tới Qt.
                            stop.set()
                            return

            self._log_follow = follow_log

        def receive(line: str) -> None:
            log_receive(line)
            port = lan_port_from_output(line)
            if port:
                self._portArrived.emit(instance_id, port, generation)

        return receive

    def begin_session(self) -> None:
        if self._log_follow is not None:
            threading.Thread(target=self._log_follow, name="nostalgia-lan-log", daemon=True).start()

    def clear(self) -> None:
        with self._lock:
            self._log_stop.set()
            self._log_follow = None
            self._generation += 1
        self.instance_id, self.port = "", 0

    @Slot(str, int, int)
    def _apply_port(self, instance_id: str, port: int, generation: int) -> None:
        with self._lock:
            if generation != self._generation:
                return
        if (instance_id, port) == (self.instance_id, self.port):
            return
        self.instance_id, self.port = instance_id, port
        self.lanOpened.emit(instance_id, port)
