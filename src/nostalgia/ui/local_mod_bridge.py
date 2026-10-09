"""Bắt kéo thả ở cửa sổ Qt để mọi trang/popup đều chọn bản chơi trước khi chép mod."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import Property, QEvent, QObject, Qt, Signal, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtQuick import QQuickView

from nostalgia.api import Launcher, LocalModImport
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.worker import WorkerBridge


class LocalModBridge(WorkerBridge):
    changed = Signal()
    reviewRequested = Signal()
    _arrived = Signal(str, object)

    def __init__(
        self, launcher: Launcher, main: LauncherBridge, content: ContentBridge, view: QQuickView
    ) -> None:
        super().__init__(view)
        self._launcher, self._main, self._content, self._view = launcher, main, content, view
        self._paths: tuple[Path, ...] = ()
        self._note, self._ignored = "", 0
        self._instance_id, self._replace_existing, self._done = "", False, False
        self._owns_storage = False
        view.installEventFilter(self)
        self._arrived.connect(self._installed)
        self.failed.connect(self._failure)
        self.busyChanged.connect(self._release_storage)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        return {
            "files": [path.name for path in self._paths],
            "count": len(self._paths),
            "ignored": self._ignored,
            "note": self._note,
            "done": self._done,
        }

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched != self._view or event.type() not in (
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
            QEvent.Type.Drop,
        ):
            return False
        drop = cast(QDropEvent | QDragEnterEvent, event)
        urls = drop.mimeData().urls()
        paths = tuple(
            dict.fromkeys(
                Path(url.toLocalFile())
                for url in urls
                if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == ".jar"
            )
        )
        if not paths:
            return False  # Giữ các DropArea modpack cũ, không bắt ảnh hoặc URL mạng.
        if self.busy or not drop.possibleActions() & Qt.DropAction.CopyAction:
            drop.ignore()
            return True
        drop.setDropAction(Qt.DropAction.CopyAction)
        drop.accept()
        if event.type() == QEvent.Type.Drop:
            self._paths, self._ignored = paths, len(urls) - len(paths)
            self.clearResult()
            self.reviewRequested.emit()
        return True

    @Slot()
    def clearResult(self) -> None:
        if not self.busy:
            self._note, self._done = "", False
            self.changed.emit()

    @Slot()
    def clear(self) -> None:
        if not self.busy:
            self._paths, self._ignored = (), 0
            self.clearResult()

    @Slot(str, bool)
    def install(self, instance_id: str, replace_existing: bool) -> None:
        if (
            self.busy
            or self._main.busy
            or self._main.storageBusy
            or self._main.gameRunning
            or self._content.busy
            or not self._paths
        ):
            return
        if instance_id not in {i.instance_id for i in self._launcher.list_instances()}:
            self._failure("Bản chơi không còn tồn tại. Hãy chọn lại.")
            return
        paths = self._paths
        self._instance_id, self._replace_existing = instance_id, replace_existing
        self._note, self._done = "", False
        self._owns_storage = True
        self._main.setStorageBusy(True)
        self.changed.emit()

        def work() -> None:
            result = self._launcher.install_local_mods(
                instance_id, paths, replace_existing=replace_existing
            )
            self._arrived.emit(instance_id, result)

        self.run_in_background(work, "Cài mod từ máy vào bản chơi đã chọn")

    @Slot()
    def retry(self) -> None:
        self.install(self._instance_id, self._replace_existing)

    def _installed(self, instance_id: str, payload: object) -> None:
        result = cast(LocalModImport, payload)
        self._note = f"Đã cài {len(result.installed)} mod."
        if result.skipped:
            self._note += f" Bỏ qua {len(result.skipped)} file đã có hoặc giống hệt."
        if result.backup_dir:
            self._note += " Bản cũ được giữ trong .nostalgia/local-mod-backups của bản chơi."
        self._done = True
        self._main.announce_instances_changed()
        if self._content.property("instanceId") == instance_id:
            self._content.refreshInstalled("mod")
        self.changed.emit()

    def _failure(self, message: str) -> None:
        self._note, self._done = message, False
        self.changed.emit()

    def _release_storage(self) -> None:
        if not self.busy and self._owns_storage:
            self._owns_storage = False
            self._main.setStorageBusy(False)
