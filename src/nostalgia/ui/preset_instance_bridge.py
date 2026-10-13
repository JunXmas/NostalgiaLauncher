"""Add bundled pack updates to the shared instance controls."""

from PySide6.QtCore import Slot

from nostalgia.ui.instance_bridge import InstanceBridge
from nostalgia.ui.instance_pack import start_builtin_update


class PresetInstanceBridge(InstanceBridge):
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
