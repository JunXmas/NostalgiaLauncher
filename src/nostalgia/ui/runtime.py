"""Điểm vào bản draft/release: giao diện mới với các dịch vụ thật, không dùng demo gateway."""

from __future__ import annotations

import logging
import os
import sys

from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication

from nostalgia import __version__
from nostalgia.api import (
    HttpRoomSyncGateway,
    HttpSocialGateway,
    Launcher,
)
from nostalgia.ui.app import enable_multisampling
from nostalgia.ui.mod_repair_bridge import ModRepairBridge
from nostalgia.ui.payment_bridge import PaymentBridge
from nostalgia.ui.preview import open_preview
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
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
        plus_enabled=False,
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

    def connect_services() -> None:
        access_token = social_gateway.access_token if social_gateway else ""
        payments.set_gateway(None)
        repair.set_gateway(None)
        synchronization.set_gateway(
            HttpRoomSyncGateway(configuration.room_sync_url, http_client, access_token)
            if access_token and configuration.room_sync_url
            else None
        )

    social.sessionChanged.connect(connect_services)
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
