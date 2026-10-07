"""Background inventory and directory watching, shared by installed-content UI."""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any

from PySide6.QtCore import (
    Property,
    QCoreApplication,
    QFileSystemWatcher,
    QObject,
    Qt,
    QTimer,
    Signal,
    Slot,
)

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.model import ContentKind
from nostalgia.errors import NostalgiaError
from nostalgia.ui.worker import WorkerBridge

logger = logging.getLogger(__name__)


class InventoryBridge(WorkerBridge):
    identified = Signal(int)
    identificationChanged = Signal()
    _inventoryReady = Signal(str, str, int)
    _installedFor = Signal(str, str)
    _installed_rows: list[dict[str, Any]]

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._target: ContentTarget | None = None
        self._installed_kind: ContentKind = "mod"
        self._inventory_worker = WorkerBridge(self)
        self._inventory_worker.busyChanged.connect(self.identificationChanged)
        self._inventory_worker.busyChanged.connect(self._continue_inventory)
        self.busyChanged.connect(self._continue_inventory)
        self._inventoryReady.connect(self._accept_inventory)
        self._installedFor.connect(self._refresh_for)
        self._inventory_seen: OrderedDict[
            tuple[str, ContentKind], tuple[tuple[tuple[str, int, int], ...], float]
        ] = OrderedDict()
        # A standalone bridge can lose its last Python reference in a worker.
        # Keep Qt timers/notifiers owned by the GUI thread and dispose there.
        owner = QCoreApplication.instance()
        self._inventory_watch = QFileSystemWatcher(owner)
        self._inventory_debounce = QTimer(owner)
        self.destroyed.connect(
            self._inventory_watch.deleteLater, Qt.ConnectionType.QueuedConnection
        )
        self.destroyed.connect(
            self._inventory_debounce.deleteLater, Qt.ConnectionType.QueuedConnection
        )
        self._inventory_debounce.setSingleShot(True)
        self._inventory_debounce.setInterval(160)
        self._inventory_watch.directoryChanged.connect(self._queue_directory_refresh)
        self._inventory_debounce.timeout.connect(self._refresh_directory)

    @Slot(str)
    def _queue_directory_refresh(self, _path: str) -> None:
        self._inventory_debounce.start()

    @Slot()
    def _refresh_directory(self) -> None:
        if self._target:
            self._reload_installed(self._installed_kind)

    def _watch_directory(self) -> None:
        desired = set()
        if self._target and self._installed_kind != "modpack":
            desired = {
                str(path)
                for path in (
                    self._target.game_dir,
                    self._launcher.content_directory(self._target, self._installed_kind),
                )
                if path.is_dir()
            }
        current = set(self._inventory_watch.directories())
        if current - desired:
            self._inventory_watch.removePaths(list(current - desired))
        if desired - current:
            self._inventory_watch.addPaths(list(desired - current))

    @Property(bool, notify=identificationChanged)
    def identifying(self) -> bool:
        return bool(self._inventory_worker.busy)

    @Slot()
    def _continue_inventory(self) -> None:
        if not self.identifying and self._target:
            self._schedule_inventory(self._target, self._installed_kind)

    @Slot(str, str, int)
    def _accept_inventory(self, instance_id: str, content_kind: str, found: int) -> None:
        if (
            self._target
            and self._target.instance_id == instance_id
            and self._installed_kind == content_kind
        ):
            self._reload_installed(self._installed_kind, automatic=False)
            if found:
                self.identified.emit(found)

    @Slot(str, str)
    def _refresh_for(self, instance_id: str, content_kind: str) -> None:
        if (
            self._target
            and self._target.instance_id == instance_id
            and self._installed_kind == content_kind
        ):
            self._reload_installed(self._installed_kind)

    def _schedule_inventory(self, target: ContentTarget, content_kind: ContentKind) -> None:
        if self.busy or self.identifying or content_kind == "modpack":
            return
        directory = self._launcher.content_directory(target, content_kind)
        signature = []
        for row in self._installed_rows:
            path = directory / (
                row["fileName"] if row["enabled"] else row["fileName"] + ".disabled"
            )
            try:
                stamp = path.stat()
                signature.append((str(row["fileName"]), stamp.st_mtime_ns, stamp.st_size))
            except OSError:
                continue
        if not signature:
            return
        key = (str(target.game_dir), content_kind)
        state = tuple(signature)
        previous = self._inventory_seen.get(key)
        if previous and previous[0] == state and previous[1] > time.monotonic():
            return
        self._inventory_seen[key] = (state, time.monotonic() + 300)
        self._inventory_seen.move_to_end(key)
        if len(self._inventory_seen) > 32:
            self._inventory_seen.popitem(last=False)

        def work() -> None:
            found = 0
            try:
                self._launcher.scan_installed_content(target, content_kind)
                self._inventoryReady.emit(target.instance_id, content_kind, 0)
                found = self._launcher.identify_installed_content(target, content_kind)
            except (NostalgiaError, OSError) as error:
                # Offline or an unknown hash does not block file management. Local
                # JAR names are already cached before the online lookup starts.
                logger.debug("automatic content identification unavailable: %s", error)
            finally:
                self._inventoryReady.emit(target.instance_id, content_kind, found)

        self._inventory_worker.run_in_background(work, "Nhận diện nội dung đã cài")

    def _reload_installed(self, content_kind: ContentKind, *, automatic: bool = True) -> None:
        raise NotImplementedError
