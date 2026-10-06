"""Tùy chọn hiển thị được lưu và áp dụng ngay, dùng chung với SettingsBridge."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher, Settings


class AppearanceBridge(QObject):
    appearanceChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._settings: Settings | None = None

    def settings_snapshot(self) -> Settings:
        if self._settings is None:
            self._settings = self._launcher.load_settings()
        return self._settings

    def _save(self, wanted: Settings) -> None:
        self._launcher.save_settings(wanted)
        self._settings = wanted

    @Property(int, notify=appearanceChanged)
    def uiScale(self) -> int:
        return self.settings_snapshot().ui_scale

    @Property(bool, notify=appearanceChanged)
    def compactUi(self) -> bool:
        return self.settings_snapshot().compact_ui

    @Property(bool, notify=appearanceChanged)
    def reducedMotion(self) -> bool:
        return self.settings_snapshot().reduced_motion

    @Property(bool, notify=appearanceChanged)
    def decorativeBackground(self) -> bool:
        return self.settings_snapshot().decorative_background

    @Property(str, notify=appearanceChanged)
    def language(self) -> str:
        return self.settings_snapshot().language

    @Slot(int, bool, bool, bool, str)
    def setAppearance(
        self, scale: int, compact: bool, reduced: bool, background: bool, language: str
    ) -> None:
        wanted = replace(
            self.settings_snapshot(),
            ui_scale=scale if scale in (100, 125, 150) else 100,
            compact_ui=compact,
            reduced_motion=reduced,
            decorative_background=background,
            language="en" if language == "en" else "vi",
        )
        self._save(wanted)
        self.appearanceChanged.emit()
