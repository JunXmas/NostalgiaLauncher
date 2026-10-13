"""Add bundled pack updates to the shared instance controls."""

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.ui.instance_bridge import InstanceBridge
from nostalgia.ui.instance_pack import start_builtin_update


class PresetInstanceBridge(InstanceBridge):
    modpackCheckChanged = Signal()
    _modpackChecked = Signal(str)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(launcher, parent)
        self._modpack_check_message = ""
        self._modpackChecked.connect(self._finish_modpack_check)

    @Property(str, notify=modpackCheckChanged)
    def modpackCheckMessage(self) -> str:
        return self._modpack_check_message

    @Slot()
    def checkModpackOnStartup(self) -> None:
        for instance in self._launcher.list_instances():
            try:
                status = self._launcher.builtin_pack_status(instance)
            except NostalgiaError:
                continue
            if status is not None:
                self.checkModpackUpdates()
                return

    @Slot()
    def checkModpackUpdates(self) -> None:
        if self.busy or self.storageBusy:
            return
        self._modpack_check_message = "Đang kiểm tra modpack…"
        self.modpackCheckChanged.emit()

        def work() -> None:
            try:
                self._launcher.refresh_builtin_modpack()
            except NostalgiaError as error:
                self._modpackChecked.emit("Chưa kiểm tra được modpack: " + str(error))
            else:
                self._modpackChecked.emit("Đã kiểm tra modpack trực tuyến.")

        self.run_in_background(work, "Kiểm tra cập nhật modpack")

    @Slot(str)
    def _finish_modpack_check(self, message: str) -> None:
        self._modpack_check_message = message
        self.announce_instances_changed()
        self.modpackCheckChanged.emit()

    @Slot(str)
    def updateModpack(self, instance_id: str) -> None:
        if self.busy or self.storageBusy or getattr(self, "_game_running", False):
            self.failed.emit(
                "Đóng Minecraft và đợi công việc hiện tại hoàn tất trước khi cập nhật."
            )
            return
        start_builtin_update(
            self._launcher,
            instance_id,
            on_progress=self.report_progress,
            on_complete=self.announce_instances_changed,
            run_in_background=self.run_in_background,
        )
