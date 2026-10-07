"""Only LAN announcements cross Qt threads; ordinary output stays batched in GameLogFeed."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot

from nostalgia.api import lan_port_from_output


class GameLanFeed(QObject):
    lanOpened = Signal(str, int)
    _portArrived = Signal(str, int, int)

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.instance_id = ""
        self.port = 0
        self._generation = 0
        self._lock = threading.Lock()
        self._portArrived.connect(self._apply_port)

    def receiver(
        self, instance_id: str, log_receive: Callable[[str], None]
    ) -> Callable[[str], None]:
        with self._lock:
            self._generation += 1
            generation = self._generation

        def receive(line: str) -> None:
            log_receive(line)
            port = lan_port_from_output(line)
            if port:
                self._portArrived.emit(instance_id, port, generation)

        return receive

    def clear(self) -> None:
        with self._lock:
            self._generation += 1
        self.instance_id, self.port = "", 0

    @Slot(str, int, int)
    def _apply_port(self, instance_id: str, port: int, generation: int) -> None:
        with self._lock:
            if generation != self._generation:
                return
        self.instance_id, self.port = instance_id, port
        self.lanOpened.emit(instance_id, port)
