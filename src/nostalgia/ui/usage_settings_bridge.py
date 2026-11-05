"""Lựa chọn thống kê chung một snapshot với các tùy chọn khác, không gắn tài khoản."""

from dataclasses import replace

from PySide6.QtCore import Property, Signal, Slot

from nostalgia.ui.appearance_bridge import AppearanceBridge


class UsageSettingsBridge(AppearanceBridge):
    usageChoiceChanged = Signal()

    @Property(str, notify=usageChoiceChanged)
    def usageChoice(self) -> str:
        return self.settings_snapshot().usage_choice_v1

    @Slot(str)
    def setUsageChoice(self, choice: str) -> None:
        if choice not in ("accepted", "declined"):
            return
        settings = self.settings_snapshot()
        if settings.usage_choice_v1 != choice:
            self._save(replace(settings, usage_choice_v1=choice))
            self.usageChoiceChanged.emit()
