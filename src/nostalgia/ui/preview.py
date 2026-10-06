"""Factory for the isolated design preview. The release entrypoint stays in app.py."""

from __future__ import annotations

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQuick import QQuickView

from nostalgia.api import Launcher
from nostalgia.ui.app import QML_DIR, build_view
from nostalgia.ui.bridge import LauncherBridge


def open_preview(launcher: Launcher) -> tuple[QQuickView, LauncherBridge]:
    """Use existing bridges and swap only the design root_item, before showing the window."""
    view, bridge = build_view(launcher)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "preview" / "MinimalPreview.qml")))
    root_item = view.rootObject()
    if root_item is not None:
        context = view.rootContext()
        context.setContextProperty("confirmDialog", root_item.findChild(QObject, "confirmDialog"))
        context.setContextProperty("donateDialog", root_item.findChild(QObject, "donateDialog"))
    view.setTitle("Nostalgia · UI design preview")
    view.resize(1440, 900)
    return view, bridge
