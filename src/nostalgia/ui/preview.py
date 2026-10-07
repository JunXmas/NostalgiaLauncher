"""Factory cho giao diện mới; bản release nối gateway thật qua runtime.py."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from nostalgia.api import (
    Launcher,
    PaymentGateway,
    RoomSyncGateway,
    ServerGateway,
    ServiceSessionStore,
    SocialGateway,
)
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.app import QML_DIR, build_view
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.host_bridge import HostBridge
from nostalgia.ui.interface_setup import InterfaceSetup
from nostalgia.ui.mod_repair_bridge import ModRepairBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.payment_bridge import PaymentBridge
from nostalgia.ui.profile_bridge import ProfileBridge
from nostalgia.ui.project_bridge import ProjectBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.server_controller import ServerController
from nostalgia.ui.server_room_bridge import ServerRoomBridge
from nostalgia.ui.settings_bridge import SettingsBridge
from nostalgia.ui.social_bridge import SocialBridge


def open_preview(
    launcher: Launcher,
    *,
    payment_gateway: PaymentGateway | None = None,
    payment_demonstration: bool = False,
    ui_setup: bool = False,
    room_sync_gateway: RoomSyncGateway | None = None,
    social_gateway: SocialGateway | None = None,
    session_store: ServiceSessionStore | None = None,
    plus_enabled: bool = True,
    server_gateway: ServerGateway | None = None,
) -> tuple[QQuickView, LauncherBridge]:
    """Use existing bridges and swap only the design root_item, before showing the window."""
    view, bridge = build_view(launcher)
    context = view.rootContext()
    context.setContextProperty("modRepairBridge", ModRepairBridge(launcher, bridge))
    multiplayer_bridge = context.contextProperty("multiplayerBridge")
    assert isinstance(multiplayer_bridge, MultiplayerBridge)
    room_sync_bridge = RoomSyncBridge(
        launcher, bridge, multiplayer_bridge, room_sync_gateway, parent=view
    )
    context.setContextProperty("roomSyncBridge", room_sync_bridge)
    social_bridge = SocialBridge(
        social_gateway,
        multiplayer_bridge,
        room_sync_bridge,
        parent=view,
        session_store=session_store,
        plus_enabled=plus_enabled,
    )
    context.setContextProperty("socialBridge", social_bridge)
    accounts = context.contextProperty("accountBridge")
    assert isinstance(accounts, AccountBridge)
    profile_bridge = ProfileBridge(
        launcher, social_bridge, social_gateway, accounts, bridge, parent=view
    )
    context.setContextProperty("profileBridge", profile_bridge)
    host_bridge = HostBridge(
        launcher,
        bridge,
        multiplayer_bridge,
        room_sync_bridge,
        social_bridge,
        plus_enabled=plus_enabled,
        parent=view,
    )
    host_bridge.connect_workflow()
    context.setContextProperty("hostBridge", host_bridge)
    context.setContextProperty("plusFeaturesEnabled", plus_enabled)
    server_bridge = ServerController(launcher, server_gateway, enabled=plus_enabled, parent=view)
    context.setContextProperty("serverBridge", server_bridge)
    server_room = ServerRoomBridge(server_bridge, multiplayer_bridge, room_sync_bridge, parent=view)
    context.setContextProperty("serverRoomBridge", server_room)
    if social_gateway is not None and social_gateway.access_token:
        social_bridge.refresh()
    elif social_gateway is not None and session_store is not None:
        QTimer.singleShot(0, social_bridge.restoreSession)
    running_application = QGuiApplication.instance()
    if running_application is not None:
        running_application.aboutToQuit.connect(room_sync_bridge.cancel)
        running_application.aboutToQuit.connect(host_bridge.stop)
        running_application.aboutToQuit.connect(social_bridge.shutdown)
        running_application.aboutToQuit.connect(profile_bridge.close)
        running_application.aboutToQuit.connect(server_bridge.shutdown)
        running_application.aboutToQuit.connect(server_room.close)
    content_bridge = context.contextProperty("contentBridge")
    assert isinstance(content_bridge, ContentBridge)
    context.setContextProperty(
        "projectBridge", ProjectBridge(launcher, bridge, content_bridge, parent=view)
    )
    context.setContextProperty(
        "paymentBridge",
        PaymentBridge(payment_gateway, demonstration=payment_demonstration, parent=view),
    )
    if ui_setup:
        settings_bridge = context.contextProperty("settingsBridge")
        assert isinstance(settings_bridge, SettingsBridge)
        interface_setup = InterfaceSetup(view, settings_bridge)
        context.setContextProperty("interfaceSetup", interface_setup)
        interface_setup.show_initial()
    else:
        view.setSource(QUrl.fromLocalFile(str(QML_DIR / "preview" / "MinimalPreview.qml")))
    root_item = view.rootObject()
    if root_item is not None:
        context = view.rootContext()
        context.setContextProperty("confirmDialog", root_item.findChild(QObject, "confirmDialog"))
        context.setContextProperty("donateDialog", root_item.findChild(QObject, "donateDialog"))
    view.setTitle("Nostalgia · UI design preview")
    view.resize(1440, 900)
    return view, bridge
