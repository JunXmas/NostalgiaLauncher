"""Entry selected at build time for the owner's unlocked local review draft only."""

from __future__ import annotations

import logging
import os
import sys

from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication

from nostalgia import __version__
from nostalgia.api import Launcher
from nostalgia.ui.app import QML_DIR, enable_multisampling
from nostalgia.ui.mod_repair_bridge import ModRepairBridge
from nostalgia.ui.payment_bridge import PaymentBridge
from nostalgia.ui.preview import open_preview
from nostalgia.ui.server_controller import ServerController
from nostalgia.ui.service_configuration_bridge import ServiceConfigurationBridge
from nostalgia.ui.social_bridge import SocialBridge
from nostalgia.ui.worker import wait_for_background
from nostalgia_draft.controls import ReviewControls
from nostalgia_draft.payment import ReviewPayment
from nostalgia_draft.repair import ReviewRepair
from nostalgia_draft.server import ReviewServer
from nostalgia_draft.social import ReviewSocial


def build_review_view(launcher: Launcher) -> QQuickView:
    social_gateway = ReviewSocial(launcher.paths.config_dir / "draft-review")
    payment_gateway = ReviewPayment()
    controls = ReviewControls(launcher, social_gateway, payment_gateway)
    view, bridge = open_preview(
        launcher,
        social_gateway=social_gateway,
        server_gateway=ReviewServer(social_gateway),
        payment_gateway=payment_gateway,
        payment_demonstration=True,
        plus_enabled=True,
        review_controller=controls,
        review_panel_url=(QML_DIR / "preview" / "ReviewPanel.qml").as_uri(),
    )
    controls.setParent(view)
    context = view.rootContext()
    context.setContextProperty(
        "serviceConfiguration", ServiceConfigurationBridge(launcher, parent=view)
    )
    social = context.contextProperty("socialBridge")
    servers = context.contextProperty("serverBridge")
    payments = context.contextProperty("paymentBridge")
    repair = context.contextProperty("modRepairBridge")
    assert isinstance(social, SocialBridge) and isinstance(servers, ServerController)
    assert isinstance(payments, PaymentBridge) and isinstance(repair, ModRepairBridge)
    controls.attach(bridge, social, servers, payments)
    repair.set_gateway(ReviewRepair(social_gateway))
    servers.checkAccess()
    application = QApplication.instance()
    if application is not None:
        application.aboutToQuit.connect(controls.cancel)
    view.setTitle("Nostalgia Launcher · " + __version__ + " · Ultimate TEST")
    return view


def main(argv: list[str] | None = None) -> int:
    enable_multisampling()
    application = QApplication(argv if argv is not None else sys.argv)
    application.setApplicationName("Nostalgia Launcher")
    application.setApplicationVersion(__version__)
    launcher = Launcher.for_environment()
    view = build_review_view(launcher)
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
        wait_for_background()
        application.processEvents()
        context = view.rootContext()
        assert context.contextProperty("socialBridge").property("account")["planName"] == "Ultimate"
        assert context.contextProperty("serverBridge").property("hasAccess")
        view.close()
        logging.warning("smoke ok · unlocked draft review")
        return 0
    result = application.exec()
    wait_for_background()
    return result
