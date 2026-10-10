"""Điểm vào bản draft/release: giao diện mới với các dịch vụ thật, không dùng demo gateway."""

from __future__ import annotations

import logging
import os
import sys

from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication

from nostalgia import __version__
from nostalgia.api import (
    HttpPaymentGateway,
    HttpRepairGateway,
    HttpRoomSyncGateway,
    HttpServerGateway,
    HttpSocialGateway,
    Launcher,
)
from nostalgia.ui.app import enable_multisampling
from nostalgia.ui.mod_repair_bridge import ModRepairBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.payment_bridge import PaymentBridge
from nostalgia.ui.preview import open_preview
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.server_controller import ServerController
from nostalgia.ui.service_configuration_bridge import ServiceConfigurationBridge
from nostalgia.ui.worker import wait_for_background


def build_release_view(launcher: Launcher) -> QQuickView:
    configuration = launcher.load_service_configuration()
    http_client = launcher.make_http_client()
    social_gateway = (
        HttpSocialGateway(configuration.account_url, http_client)
        if configuration.account_url
        else None
    )
    view, _bridge = open_preview(
        launcher,
        social_gateway=social_gateway,
        session_store=launcher.make_service_session_store(configuration.account_url)
        if social_gateway
        else None,
        plus_enabled=bool(configuration.account_url),
    )
    view.rootContext().setContextProperty(
        "serviceConfiguration", ServiceConfigurationBridge(launcher, parent=view)
    )
    payments = view.rootContext().contextProperty("paymentBridge")
    synchronization = view.rootContext().contextProperty("roomSyncBridge")
    repair = view.rootContext().contextProperty("modRepairBridge")
    assert (
        isinstance(payments, PaymentBridge)
        and isinstance(synchronization, RoomSyncBridge)
        and isinstance(repair, ModRepairBridge)
    )
    social = view.rootContext().contextProperty("socialBridge")
    multiplayer = view.rootContext().contextProperty("multiplayerBridge")
    assert isinstance(multiplayer, MultiplayerBridge)
    servers = view.rootContext().contextProperty("serverBridge")
    assert isinstance(servers, ServerController)
    repair_access_token = ""
    server_membership: tuple[object, ...] = ()

    def refresh_server_rights() -> None:
        nonlocal server_membership
        account = social.account
        next_membership = tuple(
            account.get(key)
            for key in ("accountId", "planName", "plus", "plusUntil", "plusLifetime")
        )
        if next_membership != server_membership:
            server_membership = next_membership
            servers.refreshAccess()

    def connect_repair() -> None:
        nonlocal repair_access_token
        access_token = social_gateway.access_token if social_gateway else ""
        authorized_access_token = access_token if social.account.get("plus") else ""
        if authorized_access_token != repair_access_token:
            repair_access_token = authorized_access_token
            repair.set_gateway(
                HttpRepairGateway(configuration.account_url, authorized_access_token, http_client)
                if authorized_access_token and configuration.account_url
                else None
            )

    def connect_services() -> None:
        access_token = social_gateway.access_token if social_gateway else ""
        payments.set_gateway(
            HttpPaymentGateway(configuration.account_url, access_token, http_client)
            if access_token and configuration.account_url
            else None
        )
        connect_repair()
        servers.set_gateway(
            HttpServerGateway(configuration.account_url, http_client, access_token)
            if servers.enabled and access_token and configuration.account_url
            else None
        )
        synchronization.set_gateway(
            HttpRoomSyncGateway(
                configuration.room_sync_url,
                http_client,
                access_token,
                attach_source=multiplayer.prepare_sync_source,
                download_peer=multiplayer.download_peer_file,
            )
            if access_token and configuration.room_sync_url
            else None
        )

    social.sessionChanged.connect(connect_services)
    social.changed.connect(connect_repair)
    social.changed.connect(refresh_server_rights)
    payments.paymentConfirmed.connect(social.refresh)
    payments.paymentConfirmed.connect(servers.refreshAccess)
    connect_services()
    application = QApplication.instance()
    if application is not None:
        application.aboutToQuit.connect(lambda: http_client.close())
    view.setTitle("Nostalgia Launcher · " + __version__)
    return view


def main(argv: list[str] | None = None) -> int:
    enable_multisampling()
    application = QApplication(argv if argv is not None else sys.argv)
    application.setApplicationName("Nostalgia Launcher")
    application.setApplicationVersion(__version__)
    launcher = Launcher.for_environment()
    view = build_release_view(launcher)
    if view.status() != QQuickView.Status.Ready:
        for error in view.errors():
            logging.error("%s", error.toString())
        return 1
    if not launcher.list_accounts():
        view.showMaximized()
    else:
        view.show()
    if os.environ.get("NOSTALGIA_SMOKE_TEST") == "1":
        application.processEvents()
        logging.warning("smoke ok")
        wait_for_background()
        view.close()
        return 0
    result = application.exec()
    wait_for_background()
    return result
