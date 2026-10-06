"""Run the isolated UI design preview without building or changing release UI.

    python bench/ui_minimal_preview.py
    python bench/ui_minimal_preview.py --data-dir /path/to/preview-data

By default data and settings live in a temporary directory. No game data is copied.
"""

from __future__ import annotations

import argparse
import tempfile
from dataclasses import replace
from pathlib import Path

from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication

from nostalgia.api import (
    HttpPaymentGateway,
    HttpRoomSyncGateway,
    HttpSocialGateway,
    Launcher,
    SocialGateway,
)
from nostalgia.net.http import HttpClient
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--payment-demo", action="store_true", help="QR mẫu, không chuyển tiền")
    parser.add_argument("--plus-url", default="", help="URL HTTPS của backend Plus đã triển khai")
    parser.add_argument("--plus-session-file", type=Path, help="File chứa phiên tài khoản ủng hộ")
    parser.add_argument("--room-sync-url", default="", help="Relay HTTPS hỗ trợ đồng bộ Plus")
    parser.add_argument("--accounts-url", default="", help="URL HTTPS của dịch vụ Google/bạn bè")
    parser.add_argument(
        "--social-demo", action="store_true", help="Dữ liệu bạn bè PREVIEW, không đăng nhập thật"
    )
    args = parser.parse_args()
    if args.social_demo and args.accounts_url:
        parser.error("Không ghép --social-demo và --accounts-url")
    if args.accounts_url and (args.plus_url or args.plus_session_file or args.payment_demo):
        parser.error(
            "--accounts-url cung cấp phiên Google cho Plus; không ghép chế độ thanh toán khác"
        )
    if bool(args.plus_url) != bool(args.plus_session_file):
        parser.error("--plus-url và --plus-session-file phải đi cùng nhau")
    if args.payment_demo and args.plus_url:
        parser.error("Không dùng backend thanh toán thật cùng --payment-demo")
    preview_dir = args.data_dir or Path(tempfile.mkdtemp(prefix="nostalgia-ui-preview-"))
    launcher = Launcher.for_data_dir(preview_dir / "data", preview_dir / "settings")
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    qt_application = QApplication(["Nostalgia UI preview"])
    qt_application.setApplicationName("Nostalgia UI preview")
    http_client = HttpClient(timeout_seconds=10)
    session_token = args.plus_session_file.read_text().strip() if args.plus_session_file else ""
    sync_gateway = (
        HttpRoomSyncGateway(args.room_sync_url, http_client, session_token)
        if args.room_sync_url
        else None
    )
    social_gateway: SocialGateway | None = (
        HttpSocialGateway(args.accounts_url, http_client) if args.accounts_url else None
    )
    session_store = (
        launcher.make_service_session_store(args.accounts_url) if args.accounts_url else None
    )
    if args.social_demo:
        from ui_social_demo import DemoSocialGateway

        social_gateway = DemoSocialGateway()
    if args.payment_demo:
        from ui_payment_demo import DemoPaymentGateway

        view, bridge = open_preview(
            launcher,
            payment_gateway=DemoPaymentGateway(),
            payment_demonstration=True,
            ui_setup=True,
            room_sync_gateway=sync_gateway,
            social_gateway=social_gateway,
            session_store=session_store,
        )
    elif args.plus_session_file:
        gateway = HttpPaymentGateway(args.plus_url, session_token, http_client)
        view, bridge = open_preview(
            launcher,
            payment_gateway=gateway,
            ui_setup=True,
            room_sync_gateway=sync_gateway,
            social_gateway=social_gateway,
            session_store=session_store,
        )
    else:
        view, bridge = open_preview(
            launcher,
            ui_setup=True,
            room_sync_gateway=sync_gateway,
            social_gateway=social_gateway,
            session_store=session_store,
        )
    if args.accounts_url:
        social_bridge = view.rootContext().contextProperty("socialBridge")
        payment_bridge = view.rootContext().contextProperty("paymentBridge")
        room_bridge = view.rootContext().contextProperty("roomSyncBridge")

        def connect_services() -> None:
            access_token = social_bridge.access_token()
            payment_bridge.set_gateway(
                HttpPaymentGateway(args.accounts_url, access_token, http_client)
                if access_token
                else None
            )
            if args.room_sync_url:
                room_bridge.set_gateway(
                    HttpRoomSyncGateway(args.room_sync_url, http_client, access_token)
                )

        social_bridge.sessionChanged.connect(connect_services)
    try:
        if view.status() != QQuickView.Status.Ready:
            for error in view.errors():
                print(error.toString())
            return 1
        # First launch fills the desktop while keeping standard window controls.
        if bridge.activePlayerName:
            view.show()
        else:
            view.showMaximized()
        return qt_application.exec()
    finally:
        bridge.cancelSignIn()
        wait_for_background()
        http_client.close()


if __name__ == "__main__":
    raise SystemExit(main())
