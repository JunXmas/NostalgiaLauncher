"""Factory cho giao diện mới; bản release nối gateway thật qua runtime.py."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtGui import QGuiApplication

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
from nostalgia.ui.cosmetic_bridge import CosmeticBridge
from nostalgia.ui.google_link_bridge import GoogleLinkBridge
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
from nostalgia.ui.view import LauncherView


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
    review_controller: QObject | None = None,
    review_panel_url: str = "",
) -> tuple[LauncherView, LauncherBridge]:
    """Use existing bridges and swap only the design root_item, before showing the window."""
    view, bridge = build_view(launcher)
    context = view.rootContext()
    view.bind_context_property("draftReviewController", review_controller)
    view.bind_context_property("draftReviewPanel", review_panel_url)
    view.bind_context_property("modRepairBridge", ModRepairBridge(launcher, bridge))
    multiplayer_bridge = context.contextProperty("multiplayerBridge")
    assert isinstance(multiplayer_bridge, MultiplayerBridge)
    room_sync_bridge = RoomSyncBridge(
        launcher, bridge, multiplayer_bridge, room_sync_gateway, parent=view
    )
    view.bind_context_property("roomSyncBridge", room_sync_bridge)
    social_bridge = SocialBridge(
        social_gateway,
        multiplayer_bridge,
        room_sync_bridge,
        parent=view,
        session_store=session_store,
        plus_enabled=plus_enabled,
    )
    view.bind_context_property("socialBridge", social_bridge)
    accounts = context.contextProperty("accountBridge")
    assert isinstance(accounts, AccountBridge)
    view.bind_context_property(
        "googleLinkBridge", GoogleLinkBridge(launcher, bridge, accounts, social_bridge, parent=view)
    )
    profile_bridge = ProfileBridge(
        launcher, social_bridge, social_gateway, accounts, bridge, parent=view
    )
    view.bind_context_property("profileBridge", profile_bridge)
    cosmetic_bridge = CosmeticBridge(social_bridge, social_gateway, parent=view)
    profile_bridge.saved.connect(cosmetic_bridge.refresh)
    view.bind_context_property("cosmeticBridge", cosmetic_bridge)
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
    view.bind_context_property("hostBridge", host_bridge)
    view.bind_context_property("plusFeaturesEnabled", plus_enabled)
    server_bridge = ServerController(launcher, server_gateway, enabled=plus_enabled, parent=view)
    view.bind_context_property("serverBridge", server_bridge)
    server_room = ServerRoomBridge(server_bridge, multiplayer_bridge, room_sync_bridge, parent=view)
    view.bind_context_property("serverRoomBridge", server_room)
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
        running_application.aboutToQuit.connect(cosmetic_bridge.close)
        running_application.aboutToQuit.connect(server_bridge.shutdown)
        running_application.aboutToQuit.connect(server_room.close)
    content_bridge = context.contextProperty("contentBridge")
    assert isinstance(content_bridge, ContentBridge)
    view.bind_context_property(
        "projectBridge", ProjectBridge(launcher, bridge, content_bridge, parent=view)
    )
    view.bind_context_property(
        "paymentBridge",
        PaymentBridge(payment_gateway, demonstration=payment_demonstration, parent=view),
    )
    if ui_setup:
        settings_bridge = context.contextProperty("settingsBridge")
        assert isinstance(settings_bridge, SettingsBridge)
        interface_setup = InterfaceSetup(view, settings_bridge)
        view.bind_context_property("interfaceSetup", interface_setup)
        interface_setup.show_initial()
    else:
        view.setSource(QUrl.fromLocalFile(str(QML_DIR / "preview" / "MinimalPreview.qml")))
    root_item = view.rootObject()
    if root_item is not None:
        view.bind_context_property("confirmDialog", root_item.findChild(QObject, "confirmDialog"))
        view.bind_context_property("donateDialog", root_item.findChild(QObject, "donateDialog"))
    view.setTitle("Nostalgia · UI design preview")
    view.resize(1440, 900)
    return view, bridge
