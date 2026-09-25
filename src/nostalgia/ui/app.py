"""Điểm vào của giao diện: `nostalgia-ui`.

Chỉ làm ba việc — dựng `Launcher`, dựng cầu nối, nạp QML. Mọi logic nằm ở lõi; mọi cách vẽ
nằm ở QML. File này cố ý mỏng để không có chỗ nào cho logic lén chui vào tầng giao diện.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject, QSize, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon, QSurfaceFormat
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from nostalgia import __version__
from nostalgia.api import Launcher
from nostalgia.ui.account_bridge import AccountBridge
from nostalgia.ui.block_bridge import BlockIconBridge
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import CatalogBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.import_bridge import ImportBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.notifier import Notifier
from nostalgia.ui.presence_bridge import PresenceBridge
from nostalgia.ui.settings_bridge import SettingsBridge
from nostalgia.ui.sound import SoundPlayer
from nostalgia.ui.update_bridge import UpdateBridge

# TranslationProvider.qml đọc từ điển i18n/*.json bằng XMLHttpRequest; Qt6 chặn mặc định.
os.environ.setdefault("QML_XHR_ALLOW_FILE_READ", "1")

QML_DIR = Path(__file__).resolve().parent / "qml"

logger = logging.getLogger(__name__)


MULTISAMPLE_COUNT = 4

# Phải khớp `Theme.sans`. Một chỗ đổi tên font mà quên chỗ kia thì chữ rơi về font hệ thống
# lặng lẽ — `tests/ui/test_fonts.py` gác cho hai giá trị này bằng nhau.
SANS_FAMILY = "Inter"


def enable_multisampling() -> None:
    """Bật khử răng cưa toàn cảnh (MSAA 4x).

    Phải gọi **trước** khi dựng `QApplication`: định dạng mặt vẽ mặc định được chốt lúc
    ngữ cảnh đồ hoạ ra đời, đặt sau thì không có tác dụng và cũng không báo lỗi.

    **Đo được: không đổi gì trên máy này.** `bench/ui_edge_quality.py` cho ra CÙNG một con
    số với samples=4 và samples=0, ở cả ba cảnh: giao diện tĩnh (2051), thanh bên có icon
    khối (1555), và dấu tick đang xoay giữa chừng hoạt ảnh (105). Lý do: Qt đã tự khử răng
    cưa góc bo của `Rectangle`, và vẽ chữ bằng distance field — MSAA không còn gì để làm.
    Máy này cũng không có GL phần cứng (amdgpu init hỏng, rơi về llvmpipe), nên con số trên
    chỉ nói về đường vẽ phần mềm.

    Giữ lại vì nó vô hại và là mặc định đúng trên máy có GPU thật, nhưng ĐỪNG tin rằng nó
    đang làm gì: độ nét thật của icon khối đến từ chỗ khác — `blocks.SUPERSAMPLE`, vẽ gấp
    ba rồi thu nhỏ, và đó là thứ đo được.
    """
    surface_format = QSurfaceFormat.defaultFormat()
    surface_format.setSamples(MULTISAMPLE_COUNT)
    QSurfaceFormat.setDefaultFormat(surface_format)


def load_fonts() -> None:
    """Nạp font đóng kèm, để mọi máy hiện chữ giống nhau.

    Không nhúng thì Qt rơi về font mặc định hệ thống — mỗi bản Linux một kiểu, và bản nào
    thiếu dấu tiếng Việt thì chữ nhảy font giữa câu. Cả hai họ dưới đây đều đo được
    **phủ đủ 74 ký tự có dấu** bằng `QRawFont.supportsCharacter`.

    Inter cho chữ đọc, Minecraft F2D cho nhãn viết hoa — đúng cách minecraft.net làm:
    tiêu đề kiểu pixel, thân bài font thường. F2D chỉ có một kiểu Regular, nên nó chỉ dùng
    được ở nhãn ngắn; đặt nó cho cả đoạn văn là chữ sẽ gồ ghề và không phân được cấp bậc.
    """
    fonts_dir = QML_DIR / "assets" / "fonts"
    for path in sorted(fonts_dir.glob("*.[ot]tf")):
        if QFontDatabase.addApplicationFont(str(path)) < 0:
            # Mất font là mất cả diện mạo — cả một bước chết thì phải nghe được.
            logger.warning("không nạp được font %s, giao diện sẽ rơi về font hệ thống", path.name)

    # Đặt mặc định ở tầng ứng dụng thay vì khai `font.family` ở từng file QML: 57 file không
    # phải sửa, và chỗ nào quên cũng vẫn đúng font. `instance()` khai kiểu trả về là
    # QCoreApplication (không có font) — chỉ bản QGuiApplication mới đặt được.
    application = QGuiApplication.instance()
    if isinstance(application, QGuiApplication):
        application.setFont(QFont(SANS_FAMILY))


def build_view(launcher: Launcher) -> tuple[QQuickView, LauncherBridge]:
    """Dựng khung nhìn và cầu nối.

    Tách khỏi `main` để test dựng được mà không phải chạy vòng lặp sự kiện — và để bộ chụp
    ảnh dùng lại đúng đường mà người dùng đi, chứ không dựng một bản riêng cho ảnh đẹp.
    """
    load_fonts()
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
    context.setContextProperty("blockIcons", BlockIconBridge(launcher.paths.data_dir, parent=view))
    settings_bridge = SettingsBridge(launcher, parent=view)
    context.setContextProperty("settingsBridge", settings_bridge)
    notifier = build_notifier(launcher, bridge, settings_bridge, view)
    context.setContextProperty("notifier", notifier)
    update_bridge = UpdateBridge(
        launcher, check_enabled=lambda: bool(settings_bridge.autoUpdateCheck), parent=view
    )
    update_bridge.updateAvailable.connect(
        lambda launcher_version: notifier.announce(
            "update", f"Có bản mới {launcher_version}", "Bấm Tải về ở dải xanh trên đầu cửa sổ"
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
    multiplayer_bridge.statusChanged.connect(
        lambda: presence_bridge.setRoomState(
            str(multiplayer_bridge.role), cast(int, multiplayer_bridge.joinerCount)
        )
    )
    context.setContextProperty("multiplayerBridge", multiplayer_bridge)
    import_bridge = ImportBridge(launcher, bridge, parent=view)
    context.setContextProperty("importBridge", import_bridge)
    # Đóng cửa sổ là đóng phòng: không để luồng relay sống sau launcher (luật L10).
    running_application = QGuiApplication.instance()
    if running_application is not None:
        running_application.aboutToQuit.connect(multiplayer_bridge.shutdown)
        running_application.aboutToQuit.connect(presence_bridge.shutdown)
    view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
    view.setTitle("Nostalgia Launcher")
    # Cho phép cửa sổ co nhỏ đến 1024x600 để chạy được trên màn hình 1366x768 (trừ taskbar,
    # title bar). Bố cục QML tự scale xuống nhờ ScrollView / Flickable và layout linh hoạt.
    view.setMinimumSize(QSize(1024, 600))
    view.resize(1360, 860)
    view.setSource(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    # Hộp hỏi lại dùng chung nằm ở Main.qml để phủ cả thanh bên; các trang (nạp sau, qua Loader)
    # gọi nó bằng context property thay vì phải với lên cây cha.
    root_item = view.rootObject()
    if root_item is not None:
        context.setContextProperty("confirmDialog", root_item.findChild(QObject, "confirmDialog"))
    build_tray(view, bridge, settings_bridge)
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


def build_tray(
    view: QQuickView, bridge: LauncherBridge, settings_bridge: SettingsBridge
) -> QSystemTrayIcon:
    """Khay hệ thống: ẩn cửa sổ khi game chạy, hiện lại khi game tắt — giải phóng RAM."""
    tray = QSystemTrayIcon(view.icon(), parent=view)
    tray.setToolTip("Nostalgia Launcher")
    menu = QMenu()
    show_action = menu.addAction("Hiện lại Launcher")
    show_action.triggered.connect(lambda: view.show())
    stop_action = menu.addAction("Dừng game")
    stop_action.triggered.connect(bridge.stopGame)
    menu.addSeparator()
    quit_action = menu.addAction("Thoát")
    running_app = QApplication.instance()
    if running_app is not None:
        quit_action.triggered.connect(running_app.quit)
    tray.setContextMenu(menu)

    def on_game_started(_instance_id: str) -> None:
        if settings_bridge.hideWhenGameRunning:
            view.hide()
            tray.show()

    def on_game_stopped(_exit_code: int) -> None:
        tray.hide()
        view.show()

    bridge.gameStarted.connect(on_game_started)
    bridge.gameStopped.connect(on_game_stopped)
    return tray


def main(argv: list[str] | None = None) -> int:
    """Mở cửa sổ. Trả về mã thoát của vòng lặp sự kiện Qt."""
    enable_multisampling()
    qt_application = QApplication(argv if argv is not None else sys.argv)
    qt_application.setApplicationName("Nostalgia Launcher")
    qt_application.setApplicationVersion(__version__)

    view, _bridge = build_view(Launcher.for_environment())
    if view.status() != QQuickView.Status.Ready:
        for error in view.errors():
            logger.error("%s", error.toString())
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
