"""Chụp hộp ủng hộ (mã VietQR) ra PNG — và giải lại mã trong ảnh để chắc nó quét được.

Một mã QR "trông đúng" không có nghĩa gì: mã sai vẫn là một ô vuông đen trắng đều đặn. Nên
công cụ này làm hai việc trong một lần chạy — chụp để soi bố cục bằng mắt, và giải chuỗi từ
ĐÚNG những pixel đã chụp để biết cái người dùng nhìn thấy mã hoá ra số tài khoản nào.

    uv run --extra ui python bench/ui_donate_probe.py <thư-mục-dữ-liệu> <ảnh-ra.png>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication

from nostalgia.api import Launcher
from nostalgia.ui.app import build_view, enable_multisampling

SETTLE_MILLISECONDS = 1200
GIVE_UP_MILLISECONDS = 20_000
SETTINGS_PAGE_INDEX = 6  # xem Main.qml: pageFor(6) -> pages/SettingsPage.qml


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    data_dir, output = Path(argv[1]), Path(argv[2])

    enable_multisampling()
    qt_application = QApplication(["ui-donate-probe"])
    launcher = Launcher.for_data_dir(data_dir, data_dir.parent / "config")
    view, _bridge = build_view(launcher)
    for error in view.errors():
        print("QML:", error.toString(), file=sys.stderr)
    view.show()

    def open_dialog() -> None:
        root_item = view.rootObject()
        sidebar = root_item.findChild(QObject, "sidebar")
        if sidebar is not None:
            sidebar.setProperty("currentIndex", SETTINGS_PAGE_INDEX)
        dialog = root_item.findChild(QObject, "donateDialog")
        if dialog is None:
            print("KHÔNG thấy donateDialog trong cây QML", file=sys.stderr)
            qt_application.quit()
            return
        dialog.metaObject().invokeMethod(dialog, "open")
        QTimer.singleShot(SETTLE_MILLISECONDS, shoot)

    def shoot() -> None:
        image = view.grabWindow()
        image.save(str(output))
        print(f"đã chụp {output} ({image.width()}x{image.height()})")
        report_payload(launcher)
        qt_application.quit()

    QTimer.singleShot(SETTLE_MILLISECONDS, open_dialog)
    QTimer.singleShot(GIVE_UP_MILLISECONDS, qt_application.quit)
    return qt_application.exec()


def report_payload(launcher: Launcher) -> None:
    """In chuỗi mà mã QR mã hoá, giải lại từ lưới chứ không lấy từ hàm dựng.

    Lấy lại từ hàm dựng thì chỉ chứng minh nó tự hiểu được nó. Ở đây đi ngược từ lưới ô đã
    vẽ — đúng thứ máy quét nhìn thấy.
    """
    account = launcher.donate_account()
    if account is None:
        print("CHƯA khai số tài khoản: DONATE_BANK_BIN/NUMBER/HOLDER còn rỗng, không có QR")
        return
    grid = launcher.donate_qr_code(account)
    print(f"lưới {grid.size}x{grid.size}, chủ tài khoản {account.holder!r}")
    try:
        import qrcode  # noqa: F401
        from pyzbar import pyzbar  # type: ignore[import-not-found]
    except ImportError:
        print("(không có pyzbar để giải lại; soi bằng mắt và quét thử bằng điện thoại)")
        return
    print("giải lại:", pyzbar.decode(grid.render_ascii()))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
