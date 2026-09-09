"""Đo thật trang TÀI KHOẢN: mỗi thao tác đọc đĩa mấy lần, chặn luồng giao diện bao lâu.

Cùng mục đích với `ui_screenshot.py`: biến cảm giác "lag" thành con số. Số liệu trước khi
sửa (09/2026): khởi động đọc accounts.json 8 lần, mỗi cú bấm chọn tài khoản 11 lần, thêm tài
khoản 26 lần; sau khi cầu nối giữ kho tài khoản trong RAM: 1 / 0 / 2.

    uv run --extra ui python bench/ui_account_probe.py            # offscreen, HOME cách ly
    QT_QPA_PLATFORM=xcb uv run --extra ui python bench/ui_account_probe.py   # màn hình thật

Lưu ý khi đo trên màn hình thật: đừng `grabWindow()` (vòng render đa luồng có thể treo), và
vòng `processEvents` tự nó cũng làm cửa sổ vẽ lại — muốn đếm khung hình lúc đứng yên thì phải
dùng `app.exec()` với `QTimer`, không dùng vòng lặp này.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

WORK_DIR = Path(tempfile.mkdtemp(prefix="nostalgia-probe-"))
# Đặt HOME trước khi import nostalgia: paths.py tính thư mục cấu hình lúc import.
os.environ["HOME"] = str(WORK_DIR / "home")
os.environ["XDG_CONFIG_HOME"] = str(WORK_DIR / "home/.config")
os.environ["XDG_DATA_HOME"] = str(WORK_DIR / "home/.local/share")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from nostalgia.account.model import Account  # noqa: E402
from nostalgia.api import Launcher  # noqa: E402
from nostalgia.skin.model import PlayerSkin  # noqa: E402
from nostalgia.ui.app import build_view  # noqa: E402

PLAYER_NAMES = ("JunSlayest", "Dinnerbone", "Notch")


def main() -> int:
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    launcher = Launcher.for_data_dir(WORK_DIR / "data", WORK_DIR / "config")
    for name in PLAYER_NAMES:
        launcher.add_offline_account(name)
    disk_reads = {"list_accounts": 0, "describe_skin": 0}
    original_list, original_describe = Launcher.list_accounts, Launcher.describe_skin

    def counted_list(self: Launcher) -> tuple[Account, ...]:
        disk_reads["list_accounts"] += 1
        return original_list(self)

    def counted_describe(self: Launcher, account: Account) -> PlayerSkin:
        disk_reads["describe_skin"] += 1
        return original_describe(self, account)

    patched: Any = Launcher  # thay hai phương thức lõi bằng bản đếm, chỉ trong tiến trình này
    patched.list_accounts = counted_list
    patched.describe_skin = counted_describe

    qt_application = QGuiApplication(["ui-account-probe"])
    qt_application.setApplicationVersion("0.0.0")
    view, bridge = build_view(launcher)
    root_item = view.rootObject()
    sidebar = root_item.findChild(QObject, "sidebar")
    page_loader = root_item.findChild(QObject, "pageLoader")
    assert sidebar is not None and page_loader is not None
    view.show()
    longest_stall = 0.0

    def settle(milliseconds: int) -> float:
        """Xử lý sự kiện một lúc; trả về ms luồng giao diện thực sự bận."""
        nonlocal longest_stall
        deadline = time.perf_counter() + milliseconds / 1000
        busy = longest_stall = 0.0
        while time.perf_counter() < deadline:
            started = time.perf_counter()
            qt_application.processEvents()
            took = time.perf_counter() - started
            busy += took
            longest_stall = max(longest_stall, took * 1000)
            time.sleep(0.005)
        return busy * 1000

    def report(caption: str, before: dict[str, int], busy: float) -> None:
        reads = " ".join(f"{key}+{disk_reads[key] - before[key]}" for key in disk_reads)
        print(f"{caption:<28} bận {busy:6.1f} ms, khựng dài nhất {longest_stall:5.1f} ms | {reads}")

    settle(600)
    startup = " ".join(f"{key}={count}" for key, count in disk_reads.items())
    print(f"khởi động: {startup}")
    before = dict(disk_reads)
    sidebar.setProperty("currentIndex", 3)
    report("mở trang TÀI KHOẢN", before, settle(800))
    page = page_loader.property("item")
    for name in PLAYER_NAMES[1:] + PLAYER_NAMES[:1]:
        before = dict(disk_reads)
        page.setProperty("shownName", name)
        bridge.setActiveAccount(name)
        report(f"chọn {name}", before, settle(300))
    before = dict(disk_reads)
    page.setProperty("facing", 1)
    report("xoay nhân vật", before, settle(300))
    before = dict(disk_reads)
    bridge.addOfflineAccount("Herobrine")
    report("thêm tài khoản", before, settle(1200))
    print(f"cảnh báo QML: {len(warnings)}")
    for message in warnings[:5]:
        print("  ", message.split("/qml/")[-1][:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
