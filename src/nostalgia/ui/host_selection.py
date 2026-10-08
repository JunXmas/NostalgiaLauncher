"""Danh sách mod chia sẻ: chỉ đọc đĩa trong worker, lựa chọn giữ theo từng bản chơi."""

from dataclasses import replace
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.model.pack import SharedMod
from nostalgia.ui.worker import WorkerBridge


class HostModSelection(WorkerBridge):
    changed = Signal()
    _arrived = Signal(object, int, str)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._instance_id = ""
        self._mods: tuple[SharedMod, ...] = ()
        self._ready = False
        self._arrived.connect(self._apply)

    @Property(list, notify=changed)
    def mods(self) -> list[dict[str, Any]]:
        return [
            {
                "path": mod.relative_path,
                "title": mod.title,
                "fileName": mod.file_name,
                "icon": mod.icon_url,
                "enabled": mod.enabled,
                "shared": mod.shared,
            }
            for mod in self._mods
        ]

    @Property(int, notify=changed)
    def selectedCount(self) -> int:
        return sum(mod.shared for mod in self._mods)

    @Property(bool, notify=changed)
    def ready(self) -> bool:
        return self._ready

    def pending_for(self, instance_id: str) -> bool:
        return self._instance_id == instance_id and not self._ready

    def excluded_for(self, instance_id: str) -> frozenset[str] | None:
        return (
            frozenset(mod.relative_path for mod in self._mods if not mod.shared)
            if self._instance_id == instance_id and self._ready
            else None
        )

    @Slot(str)
    def selectInstance(self, instance_id: str) -> None:
        self._instance_id, self._mods = instance_id, ()
        self._ready = False
        generation = self.next_generation()
        self.changed.emit()
        if instance_id:

            def read_mods() -> None:
                try:
                    mods = self._launcher.list_room_share_mods(instance_id)
                    self._arrived.emit(mods, generation, "")
                except NostalgiaError as error:
                    self._arrived.emit((), generation, str(error))

            self.run_in_background(
                read_mods,
                "Đang đọc mod để chia sẻ…",
            )

    @Slot(str, bool)
    def setShared(self, relative_path: str, shared: bool) -> None:
        if self._ready:
            self._mods = tuple(
                replace(mod, shared=shared) if mod.relative_path == relative_path else mod
                for mod in self._mods
            )
            self.changed.emit()

    @Slot(bool)
    def selectAll(self, shared: bool) -> None:
        if self._ready:
            self._mods = tuple(replace(mod, shared=shared) for mod in self._mods)
            self.changed.emit()

    @Slot(object, int, str)
    def _apply(self, mods: tuple[SharedMod, ...], generation: int, message: str) -> None:
        if self.is_current(generation):
            self._mods = mods
            self._ready = not message
            self.changed.emit()
            if message:
                self.failed.emit(message)
