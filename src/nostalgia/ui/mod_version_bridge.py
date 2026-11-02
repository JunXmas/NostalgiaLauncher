"""Chọn phiên bản của mod đã cài; công việc ghi đĩa giữ khoá chung của giao diện."""

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from nostalgia.api import Launcher, ProjectVersion
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.worker import WorkerBridge


@dataclass(frozen=True, slots=True)
class _Choices:
    versions: tuple[ProjectVersion, ...]
    current_id: str
    receipt_id: str


class ModVersionBridge(WorkerBridge):
    changed = Signal()
    opened = Signal()
    dismissed = Signal()
    _arrived = Signal(object, int)
    _completed = Signal(str, int)

    def __init__(self, launcher: Launcher, bridge: LauncherBridge, content: ContentBridge) -> None:
        super().__init__(bridge.parent())
        self._launcher, self._main, self._content = launcher, bridge, content
        self._instance_id = self._file_name = self._current_id = self._receipt_id = ""
        self._note = self._pending = ""
        self._versions: tuple[ProjectVersion, ...] = ()
        self._changing = False
        self._arrived.connect(self._apply_choices)
        self._completed.connect(self._apply_change)
        self.failed.connect(self._failure)
        content.targetChanged.connect(self.reset)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        return {
            "fileName": self._file_name,
            "note": self._note,
            "canUndo": bool(self._receipt_id),
            "versions": [
                {
                    "versionId": release.version_id,
                    "number": release.version_number,
                    "type": release.version_type,
                    "published": release.date_published[:10],
                    "current": release.version_id == self._current_id,
                }
                for release in self._versions
            ],
        }

    @Slot()
    def reset(self) -> None:
        self.next_generation()
        self._instance_id = self._file_name = self._current_id = self._receipt_id = ""
        self._versions = ()
        self._note = ""
        self.changed.emit()
        self.dismissed.emit()

    @Slot(str, str)
    def open(self, instance_id: str, file_name: str) -> None:
        if self.busy:
            return
        self._instance_id, self._file_name = instance_id, file_name
        self._versions, self._note = (), ""
        generation = self.next_generation()
        self.changed.emit()
        self.opened.emit()

        def fetch() -> None:
            target = self._launcher.describe_content_target(instance_id)
            current = next(
                (
                    mod.version_id
                    for mod in self._launcher.list_installed_content(target, "mod")
                    if mod.file_name == file_name
                ),
                "",
            )
            self._arrived.emit(
                _Choices(
                    self._launcher.fetch_mod_versions(instance_id, file_name),
                    current,
                    self._launcher.latest_mod_version_change(instance_id),
                ),
                generation,
            )

        self.run_in_background(fetch, "Đang tải phiên bản mod tương thích…")

    def _blocked(self) -> bool:
        if self.busy or self._main.busy or self._main.storageBusy:
            return True
        if self._main.gameRunning:
            self._failure("Tắt Minecraft trước khi đổi hoặc hoàn tác phiên bản mod.")
            return True
        return not self._instance_id

    @Slot(str)
    def apply(self, version_id: str) -> None:
        if (
            self._blocked()
            or version_id == self._current_id
            or not any(release.version_id == version_id for release in self._versions)
        ):
            return
        generation = self.next_generation()
        self._pending, self._note, self._changing = version_id, "", True
        self._main.setStorageBusy(True)
        instance_id, file_name = self._instance_id, self._file_name

        def work() -> None:
            receipt = self._launcher.swap_mod_version(
                instance_id,
                file_name,
                version_id,
                lambda: bool(self._main.gameRunning),
                on_progress=self._main.report_progress,
            )
            self._completed.emit(receipt, generation)

        self.run_in_background(work, "Đang đổi phiên bản và giữ bản trước để hoàn tác…")

    @Slot()
    def undo(self) -> None:
        if self._blocked() or not self._receipt_id:
            return
        generation = self.next_generation()
        instance_id, receipt_id = self._instance_id, self._receipt_id
        self._note, self._changing = "", True
        self._main.setStorageBusy(True)

        def work() -> None:
            self._launcher.undo_mod_version(
                instance_id, receipt_id, lambda: bool(self._main.gameRunning)
            )
            self._completed.emit("", generation)

        self.run_in_background(work, "Đang hoàn tác phiên bản mod…")

    @Slot(object, int)
    def _apply_choices(self, choices: _Choices, generation: int) -> None:
        if self.is_current(generation):
            self._versions, self._current_id, self._receipt_id = (
                choices.versions,
                choices.current_id,
                choices.receipt_id,
            )
            self.changed.emit()

    @Slot(str, int)
    def _apply_change(self, receipt_id: str, generation: int) -> None:
        self._main.setStorageBusy(False)
        self._changing = False
        if not self.is_current(generation):
            return
        self._content.refreshInstalled("mod")
        self._receipt_id = receipt_id
        if receipt_id:
            self._current_id = self._pending
            self._file_name = next(
                release.file_name
                for release in self._versions
                if release.version_id == self._pending
            )
            self._note = "Đã đổi phiên bản. Bản trước được giữ để hoàn tác."
        else:
            self.reset()
        self.changed.emit()

    @Slot(str)
    def _failure(self, message: str) -> None:
        if self._changing:
            self._changing = False
            self._main.setStorageBusy(False)
        self._note = message
        self.changed.emit()
