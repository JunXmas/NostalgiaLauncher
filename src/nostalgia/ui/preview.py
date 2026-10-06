"""Factory for the isolated design preview. The release entrypoint stays in app.py."""

from __future__ import annotations

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQuick import QQuickView

from nostalgia.api import Launcher, PaymentGateway
from nostalgia.ui.app import QML_DIR, build_view
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.payment_bridge import PaymentBridge
from nostalgia.ui.project_bridge import ProjectBridge


def open_preview(
    launcher: Launcher,
    *,
    payment_gateway: PaymentGateway | None = None,
    payment_demonstration: bool = False,
) -> tuple[QQuickView, LauncherBridge]:
    """Use existing bridges and swap only the design root_item, before showing the window."""
    view, bridge = build_view(launcher)
    context = view.rootContext()
    content_bridge = context.contextProperty("contentBridge")
    assert isinstance(content_bridge, ContentBridge)
    context.setContextProperty(
        "projectBridge", ProjectBridge(launcher, bridge, content_bridge, parent=view)
    )
    context.setContextProperty(
        "paymentBridge",
        PaymentBridge(payment_gateway, demonstration=payment_demonstration, parent=view),
    )
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "preview" / "MinimalPreview.qml")))
    root_item = view.rootObject()
    if root_item is not None:
        context = view.rootContext()
        context.setContextProperty("confirmDialog", root_item.findChild(QObject, "confirmDialog"))
        context.setContextProperty("donateDialog", root_item.findChild(QObject, "donateDialog"))
    view.setTitle("Nostalgia · UI design preview")
    view.resize(1440, 900)
    return view, bridge
