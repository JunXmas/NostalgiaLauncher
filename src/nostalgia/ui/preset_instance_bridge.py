"""Add bundled pack updates to the shared instance controls."""

from PySide6.QtCore import Slot

from nostalgia.ui.instance_bridge import InstanceBridge
from nostalgia.ui.instance_pack import start_builtin_update


class PresetInstanceBridge(InstanceBridge):
    @Slot(str)
    def updateModpack(self, instance_id: str) -> None:
        start_builtin_update(self, instance_id)
