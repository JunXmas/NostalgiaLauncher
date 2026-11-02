"""Chụp giao diện ra PNG mà không cần màn hình.

Không phải bench đo tốc độ, nhưng ở cùng chỗ vì cùng mục đích: **biến một thứ chủ quan thành
thứ nhìn được**. Giao diện chỉ có thể nói là đúng khi đã nhìn thấy nó, và ảnh chụp là cách
duy nhất để làm điều đó trong một phiên không có màn hình.

    uv run --extra ui python bench/ui_screenshot.py <thư-mục-dữ-liệu> <ảnh-ra.png> [cảnh ...]

Không ghi cảnh thì chụp trang chủ vào đúng `<ảnh-ra.png>`. Có cảnh thì mỗi cảnh một file
`<ảnh-ra>-<cảnh>.png`. Cảnh: home, instances, library, accounts, friends, log, settings,
cosmetic, create, import, backup, restore, manage, drop.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QTimer
from PySide6.QtWidgets import QApplication

from nostalgia.api import Launcher
from nostalgia.ui.app import enable_multisampling
from nostalgia.ui.window import open_window as open_window

SETTLE_MILLISECONDS = 1500
GIVE_UP_MILLISECONDS = 120_000
PAGES = {
    "home": 0,
    "instances": 1,
    "library": 2,
    "accounts": 3,
    "friends": 4,
    "log": 5,
    "settings": 6,
    "cosmetic": 7,
}
# Cảnh hộp thoại: (trang, objectName của hộp, hàm QML mở hộp)
DIALOGS = {
    "create": (1, "modernCreateDialog", "openDialog"),
    "import": (1, "modernImportDialog", "openDialog"),
    "backup": (1, "modernBackupDialog", "openDialog"),
}


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    data_dir = Path(argv[1])
    output = Path(argv[2])
    scenes = argv[3:]

    # Trước QApplication, đúng thứ tự mà app thật dùng — nếu không, ảnh đo được sẽ
    # không phải thứ người dùng nhìn thấy.
    enable_multisampling()
    qt_application = QApplication(["ui-screenshot"])
    qt_application.setApplicationVersion("0.1.0")
    view, bridge = open_window(Launcher.for_data_dir(data_dir, data_dir.parent / "config"))
    for error in view.errors():
        print("QML:", error.toString(), file=sys.stderr)
    root_item = view.rootObject()
    root_item.setProperty("sessionSkipped", True)
    view.show()
    pending = list(scenes) or ["home"]

    def target(scene: str) -> Path:
        return output if not scenes else output.with_name(f"{output.stem}-{scene}.png")

    def close_dialogs() -> None:
        for _page, name, _opener in DIALOGS.values():
            dialog = root_item.findChild(QObject, name)
            if dialog is not None:
                dialog.setProperty("visible", False)
        drop = root_item.findChild(QObject, "packDropArea")
        if drop is not None:
            drop.setProperty("holdingPack", False)

    def stage(scene: str) -> None:
        close_dialogs()
        if scene in PAGES:
            root_item.setProperty("currentIndex", PAGES[scene])
        elif scene in DIALOGS:
            page, name, opener = DIALOGS[scene]
            root_item.setProperty("currentIndex", page)
            dialog = root_item.findChild(QObject, name)
            if dialog is None:
                print(f"không thấy {name}", file=sys.stderr)
            else:
                # Hàm QML có tham số (vd `openDialog(selectedId)`) chỉ gọi được qua bản QVariant.
                if scene == "backup":
                    QMetaObject.invokeMethod(dialog, opener, Q_ARG("QVariant", ""))
                else:
                    QMetaObject.invokeMethod(dialog, opener)
        elif scene == "restore":
            # Đúng đường người dùng: Xuất modpack → "Khôi phục dữ liệu cũ" (đóng hộp xuất rồi mở).
            root_item.setProperty("currentIndex", 1)
            exporter = root_item.findChild(QObject, "modernBackupDialog")
            if exporter is not None:
                QMetaObject.invokeMethod(exporter, "openDialog", Q_ARG("QVariant", ""))
                exporter.setProperty("legacyRequested", True)
                QTimer.singleShot(400, lambda: QMetaObject.invokeMethod(exporter, "close"))
        elif scene == "manage":
            root_item.setProperty("currentIndex", 1)
            QTimer.singleShot(300, open_manager)
        elif scene == "drop":
            root_item.setProperty("currentIndex", 1)
            QTimer.singleShot(300, light_drop_overlay)

    def open_manager() -> None:
        # Quản lý bản chơi đầu tiên, tab "Xuất & dữ liệu" (sao lưu, thùng rác, xoá).
        manager = root_item.findChild(QObject, "modernInstanceManager")
        rows = bridge.property("instances")
        if manager is not None and rows:
            QMetaObject.invokeMethod(manager, "openFor", Q_ARG("QVariant", rows[0]))
            manager.setProperty("section", 3)

    def light_drop_overlay() -> None:
        # Kéo thật cần cửa sổ có màn hình; bật thẳng trạng thái "đang giữ modpack" để soi lớp phủ.
        drop = root_item.findChild(QObject, "packDropArea")
        if drop is not None:
            drop.setProperty("holdingPack", True)

    def next_scene() -> None:
        if not pending:
            qt_application.quit()
            return
        scene = pending.pop(0)
        stage(scene)
        QTimer.singleShot(SETTLE_MILLISECONDS, lambda: shoot(scene))

    def shoot(scene: str) -> None:
        image = view.grabWindow()
        path = target(scene)
        image.save(str(path))
        print(f"đã chụp {path} ({image.width()}x{image.height()})")
        next_scene()

    # Đợi một nhịp cho hoạt ảnh xuất hiện chạy xong, rồi mới chụp.
    QTimer.singleShot(SETTLE_MILLISECONDS, next_scene)
    # Phao cứu sinh: không bao giờ để công cụ treo, kể cả khi Qt kẹt.
    QTimer.singleShot(GIVE_UP_MILLISECONDS, qt_application.quit)
    return qt_application.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
