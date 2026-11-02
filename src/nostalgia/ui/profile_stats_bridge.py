"""Nạp số liệu trên luồng nền và chỉ hiện khi đang mở hồ sơ của chính người chơi."""

from typing import Any, cast

from PySide6.QtCore import Property, Signal, Slot

from nostalgia.api import Launcher, ProfileStats
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.profile_bridge import ProfileBridge
from nostalgia.ui.worker import WorkerBridge


class ProfileStatsBridge(WorkerBridge):
    changed = Signal()
    _arrived = Signal(object, int)

    def __init__(
        self, launcher: Launcher, profile_bridge: ProfileBridge, main: LauncherBridge
    ) -> None:
        super().__init__(profile_bridge.parent())
        self._launcher, self._profile = launcher, profile_bridge
        self._stats: ProfileStats | None = None
        self._arrived.connect(self._apply)
        profile_bridge.loaded.connect(self.refresh)
        profile_bridge.cleared.connect(self.clear)
        main.instancesChanged.connect(self.refresh)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        stats = self._stats or ProfileStats()
        return {
            "available": self._stats is not None,
            "playtime": stats.playtime_text,
            "launches": stats.launch_count,
            "worlds": stats.world_count,
            "instances": stats.instance_count,
            "favoriteVersion": stats.favorite_version,
        }

    @Slot()
    def clear(self) -> None:
        self.next_generation()
        self._stats = None
        self.changed.emit()

    @Slot()
    def refresh(self) -> None:
        if not cast(dict[str, Any], self._profile.property("details")).get("mine"):
            self.clear()
            return
        generation = self.next_generation()
        self.run_in_background(
            lambda: self._arrived.emit(self._launcher.load_profile_stats(), generation),
            "Đang đọc thống kê chơi trên máy này…",
        )

    @Slot(object, int)
    def _apply(self, stats: ProfileStats, generation: int) -> None:
        if self.is_current(generation):
            self._stats = stats
            self.changed.emit()
