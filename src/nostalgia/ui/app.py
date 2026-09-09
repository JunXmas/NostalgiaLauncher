"""Điểm vào của giao diện: `nostalgia-ui`.

Chỉ làm ba việc — dựng `Launcher`, dựng cầu nối, nạp QML. Mọi logic nằm ở lõi; mọi cách vẽ
nằm ở QML. File này cố ý mỏng để không có chỗ nào cho logic lén chui vào tầng giao diện.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QSize, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQuick import QQuickView

from nostalgia import __version__
from nostalgia.api import Launcher
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import CatalogBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.notifier import Notifier
from nostalgia.ui.presence_bridge import PresenceBridge
from nostalgia.ui.settings_bridge import SettingsBridge
from nostalgia.ui.sound import SoundPlayer
from nostalgia.ui.update_bridge import UpdateBridge

QML_DIR = Path(__file__).resolve().parent / "qml"


def build_view(launcher: Launcher) -> tuple[QQuickView, LauncherBridge]:
    """Dựng khung nhìn và cầu nối.

    Tách khỏi `main` để test dựng được mà không phải chạy vòng lặp sự kiện — và để bộ chụp
    ảnh dùng lại đúng đường mà người dùng đi, chứ không dựng một bản riêng cho ảnh đẹp.
    """
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    # Icon cửa sổ / thanh tác vụ: cùng chiếc lá với logo ở thanh bên và icon bộ cài.
    view.setIcon(QIcon(str(QML_DIR / "assets" / "logo.png")))
    # Gắn cầu nối vào khung nhìn: Qt sẽ huỷ chúng **sau** cây QML, nên không còn cảnh báo
    # "bridge is null" ở những ràng buộc còn sống trong lúc đóng cửa sổ.
    bridge = LauncherBridge(launcher, parent=view)
    context = view.rootContext()
    context.setContextProperty("bridge", bridge)
    context.setContextProperty("contentBridge", ContentBridge(launcher, bridge, parent=view))
    context.setContextProperty("accountBridge", AccountBridge(launcher, bridge, parent=view))
    context.setContextProperty("catalogBridge", CatalogBridge(launcher, bridge, parent=view))
    settings_bridge = SettingsBridge(launcher, parent=view)
    context.setContextProperty("settingsBridge", settings_bridge)
    notifier = build_notifier(launcher, bridge, settings_bridge, view)
    context.setContextProperty("notifier", notifier)
    update_bridge = UpdateBridge(
        launcher, check_enabled=lambda: bool(settings_bridge.autoUpdateCheck), parent=view
    )
    update_bridge.updateAvailable.connect(
        lambda launcher_version: notifier.announce(
            "update", f"Có bản mới {launcher_version}", "Mở CÀI ĐẶT → Cập nhật để tải"
        )
    )
    context.setContextProperty("updateBridge", update_bridge)
    presence_bridge = PresenceBridge(
        bridge,
        read_settings=lambda: (
            bool(settings_bridge.discordPresence),
            str(settings_bridge.discordApplicationId),
        ),
        instance_label=lambda instance_id: instance_label(launcher, instance_id),
        parent=view,
    )
    context.setContextProperty("presenceBridge", presence_bridge)
    multiplayer_bridge = MultiplayerBridge(launcher, parent=view)
    context.setContextProperty("multiplayerBridge", multiplayer_bridge)
    # Đóng cửa sổ là đóng phòng: không để luồng relay sống sau launcher (luật L10).
    running_application = QGuiApplication.instance()
    if running_application is not None:
        running_application.aboutToQuit.connect(multiplayer_bridge.shutdown)
        running_application.aboutToQuit.connect(presence_bridge.shutdown)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setTitle("Nostalgia Launcher")
    # Bố cục trang chủ neo thẻ vào ảnh hero theo toạ độ tuyệt đối; dưới cỡ này các thẻ bắt
    # đầu đè nhau, nên khoá cửa sổ không cho nhỏ hơn thay vì vẽ đè.
    view.setMinimumSize(QSize(1280, 800))
    view.resize(1360, 860)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    return view, bridge


def instance_label(launcher: Launcher, instance_id: str) -> str:
    return next(
        (i.label for i in launcher.list_instances() if i.instance_id == instance_id),
        instance_id,
    )


def build_notifier(
    launcher: Launcher, bridge: LauncherBridge, settings_bridge: SettingsBridge, view: QQuickView
) -> Notifier:
    """Toast + chuông cho game khởi động / thoát / cài xong, và blip giao diện; mỗi thứ một
    công tắc ở CÀI ĐẶT."""
    return Notifier(
        bridge,
        player=SoundPlayer(launcher.paths.data_dir / "cache" / "sounds"),
        sound_enabled=lambda: bool(settings_bridge.notificationSound),
        ui_sound_enabled=lambda: bool(settings_bridge.uiSound),
        instance_label=lambda instance_id: instance_label(launcher, instance_id),
        parent=view,
    )


def main(argv: list[str] | None = None) -> int:
    """Mở cửa sổ. Trả về mã thoát của vòng lặp sự kiện Qt."""
    qt_application = QGuiApplication(argv if argv is not None else sys.argv)
    qt_application.setApplicationName("Nostalgia Launcher")
    qt_application.setApplicationVersion(__version__)

    view, _bridge = build_view(Launcher.for_environment())
    if view.status() != QQuickView.Status.Ready:
        for error in view.errors():
            print(error.toString(), file=sys.stderr)
        return 1
    view.show()
    if os.environ.get("NOSTALGIA_SMOKE_TEST") == "1":
        # Workflow release chạy gói đóng sẵn trên cả ba hệ với biến này: dựng xong cửa sổ
        # (QML nạp, cầu nối, tài nguyên) là đủ bằng chứng gói chạy — không vào vòng lặp.
        print("smoke ok")
        return 0
    return qt_application.exec()


if __name__ == "__main__":
    sys.exit(main())
