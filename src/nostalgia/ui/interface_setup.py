"""Điều phối hai giao diện trong preview; giữ nguyên cầu nối và dữ liệu khi đổi."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtQuick import QQuickView

from nostalgia.ui.app import QML_DIR
from nostalgia.ui.settings_bridge import SettingsBridge


class InterfaceSetup(QObject):
    def __init__(self, view: QQuickView, settings_bridge: SettingsBridge) -> None:
        super().__init__(view)
        self._view = view
        self._settings_bridge = settings_bridge
        self._return_to_settings = False
        settings_bridge.interfaceStyleChanged.connect(self._queue_selected)

    def show_initial(self) -> None:
        """Chưa chọn thì mở thiết lập, đã chọn thì khôi phục giao diện đã lưu."""
        style = self._settings_bridge.settings_snapshot().interface_style
        self._show_source(style)

    def _queue_selected(self) -> None:
        # Đợi sự kiện bấm kết thúc rồi mới hủy cây QML đang phát tín hiệu.
        QTimer.singleShot(0, self._show_selected)

    def _show_selected(self) -> None:
        style = self._settings_bridge.settings_snapshot().interface_style
        self._show_source(style)

    def _show_source(self, style: str) -> None:
        path = QML_DIR / (
            "Main.qml"
            if style == "classic"
            else "preview/MinimalPreview.qml"
            if style == "modern"
            else "preview/InterfaceChooser.qml"
        )
        self._view.setSource(QUrl.fromLocalFile(str(path)))
        if self._view.status() != QQuickView.Status.Ready:
            return
        root_item = self._view.rootObject()
        context = self._view.rootContext()
        for name in ("confirmDialog", "donateDialog"):
            context.setContextProperty(name, root_item.findChild(QObject, name))
        if style and self._return_to_settings:
            sidebar = root_item.findChild(QObject, "sidebar")
            if sidebar is not None:
                sidebar.setProperty("currentIndex", 6)
            elif root_item.metaObject().indexOfProperty("currentIndex") >= 0:
                root_item.setProperty("sessionSkipped", True)
                root_item.setProperty("currentIndex", 6)

    def _is_busy(self) -> bool:
        context = self._view.rootContext()
        for name in ("bridge", "accountBridge", "contentBridge", "storageBridge", "importBridge"):
            control = context.contextProperty(name)
            if isinstance(control, QObject) and control.property("busy"):
                return True
        return False

    @Slot()
    def openChooser(self) -> None:
        if not self._is_busy():
            self._return_to_settings = True
            QTimer.singleShot(0, lambda: self._show_source(""))

    @Slot(str)
    def choose(self, style: str) -> None:
        if not self._is_busy():
            self._settings_bridge.setInterfaceStyle(style)

    @Slot()
    def cancel(self) -> None:
        if self._settings_bridge.settings_snapshot().interface_style:
            QTimer.singleShot(0, self._show_selected)
