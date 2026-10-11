"""Giữ cầu nối Python sống cùng cửa sổ sử dụng chúng trong QML."""

from __future__ import annotations

from PySide6.QtQuick import QQuickView


class LauncherView(QQuickView):
    def __init__(self) -> None:
        super().__init__()
        self._context_references: dict[str, object] = {}

    def bind_context_property(self, name: str, value: object) -> None:
        # QQmlContext không sở hữu QObject; giữ cả wrapper Python để các Signal
        # và Slot động không bị GC thu hồi khi QML vẫn đang sử dụng chúng.
        self._context_references[name] = value
        self.rootContext().setContextProperty(name, value)
