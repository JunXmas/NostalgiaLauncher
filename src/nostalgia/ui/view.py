"""Giữ cầu nối Python sống cùng cửa sổ sử dụng chúng trong QML."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtGui import QWindow
from PySide6.QtQuick import QQuickView

if TYPE_CHECKING:
    from nostalgia.ui.bridge import LauncherBridge


class LauncherView(QQuickView):
    effectsEnabledChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._context_references: dict[str, object] = {}
        self._game_bridge: LauncherBridge | None = None
        self._effects_enabled = False
        # Qt mặc định giữ cả scene graph và ngữ cảnh GPU khi cửa sổ bị thu nhỏ.
        # Cho phép thu hồi chúng, giữ nguyên cây QML/cầu nối/phòng chơi chung.
        self.setPersistentSceneGraph(False)
        self.setPersistentGraphics(False)
        self.visibilityChanged.connect(self._refresh_effects)
        self.activeChanged.connect(self._refresh_effects)

    @Property(bool, notify=effectsEnabledChanged)
    def effectsEnabled(self) -> bool:
        return self._effects_enabled

    def watch_game(self, bridge: LauncherBridge) -> None:
        self._game_bridge = bridge
        bridge.gameRunningChanged.connect(self._refresh_effects)
        self._refresh_effects()

    @Slot()
    def _refresh_effects(self) -> None:
        shown = self.isVisible() and self.visibility() != QWindow.Visibility.Minimized
        playing = self._game_bridge is not None and bool(self._game_bridge.gameRunning)
        enabled = shown and (not playing or self.isActive())
        if enabled != self._effects_enabled:
            self._effects_enabled = enabled
            self.effectsEnabledChanged.emit()
        if not shown:
            self.releaseResources()

    def bind_context_property(self, name: str, value: object) -> None:
        # QQmlContext không sở hữu QObject; giữ cả wrapper Python để các Signal
        # và Slot động không bị GC thu hồi khi QML vẫn đang sử dụng chúng.
        self._context_references[name] = value
        self.rootContext().setContextProperty(name, value)
