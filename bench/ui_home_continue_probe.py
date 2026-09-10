"""Đo thật ô CHƠI TIẾP: quét thế giới mất bao lâu, và trang chủ có vẽ liên tục khi đứng yên không.

Cùng mục đích với `ui_create_dialog_probe.py`: biến lo ngại "lag" thành con số. Dựng 3 bản chơi
x 20 thế giới giả (level.dat NBT thật, dựng bằng tests/nbt_fixture.py), rồi đo ms luồng chính
khi đọc `recentWorlds` lần đầu (quét + đọc tối đa 12 file mỗi bản chơi), khi game tắt (quét lại)
và khi đứng yên.

    uv run --extra ui python bench/ui_home_continue_probe.py            # offscreen, HOME cách ly
"""

from __future__ import annotations

import base64
import os
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

WORK_DIR = Path(tempfile.mkdtemp(prefix="nostalgia-probe-continue-"))
# Đặt HOME trước khi import nostalgia: paths.py tính thư mục cấu hình lúc import.
os.environ["HOME"] = str(WORK_DIR / "home")
os.environ["XDG_CONFIG_HOME"] = str(WORK_DIR / "home/.config")
os.environ["XDG_DATA_HOME"] = str(WORK_DIR / "home/.local/share")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("NOSTALGIA_SILENT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

from PySide6.QtCore import QObject, qInstallMessageHandler  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402

from nbt_fixture import tiny_png, write_servers, write_world  # noqa: E402
from nostalgia.api import Instance, Launcher  # noqa: E402
from nostalgia.ui.app import build_view  # noqa: E402

INSTANCE_COUNT = 3
WORLDS_PER_INSTANCE = 20
SERVERS_PER_INSTANCE = 5


def seed(launcher: Launcher) -> None:
    now_ms = int(time.time() * 1000)
    for number in range(INSTANCE_COUNT):
        instance = launcher.create_instance(
            Instance(instance_id=f"ban-{number}", version_id="1.20.1", display_name=f"Bản {number}")
        )
        game_dir = launcher.instance_game_dir(instance)
        for world_number in range(WORLDS_PER_INSTANCE):
            write_world(
                game_dir,
                f"w{world_number:02d}",
                f"Thế giới {world_number}",
                now_ms - world_number * 60_000,
            )
        icon = base64.b64encode(tiny_png()).decode()
        write_servers(
            game_dir,
            [
                (f"Server {n}", f"s{n}.example:25565", icon, False)
                for n in range(SERVERS_PER_INSTANCE)
            ],
        )


def main() -> int:
    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    launcher = Launcher.for_data_dir(WORK_DIR / "data", WORK_DIR / "config")
    launcher.add_offline_account("JunSlayest")
    seed(launcher)
    qt_application = QGuiApplication(["ui-home-continue-probe"])
    qt_application.setApplicationVersion("0.0.0")
    view, bridge = build_view(launcher)
    root_item = view.rootObject()
    assert root_item is not None
    view.show()

    def settle(milliseconds: int) -> float:
        deadline = time.perf_counter() + milliseconds / 1000
        busy = 0.0
        while time.perf_counter() < deadline:
            started = time.perf_counter()
            qt_application.processEvents()
            busy += time.perf_counter() - started
            time.sleep(0.002)
        return busy * 1000

    def measure(caption: str, action: Callable[[], object]) -> None:
        started = time.perf_counter()
        action()
        blocked = (time.perf_counter() - started) * 1000
        busy = settle(700)
        print(f"{caption:<28} đứng {blocked:7.1f} ms | luồng chính bận {busy:6.1f} ms / 700")

    settle(800)
    card = root_item.findChild(QObject, "continueCard")
    assert card is not None
    shown = len(bridge.property("recentWorlds"))
    shown_servers = len(bridge.property("recentServers"))
    print(
        f"thế giới trên đĩa: {INSTANCE_COUNT * WORLDS_PER_INSTANCE}, hàng hiện: {shown}; "
        f"server trên đĩa: {INSTANCE_COUNT * SERVERS_PER_INSTANCE}, hàng hiện: {shown_servers}"
    )
    measure("quét lại khi game tắt", lambda: bridge.gameStopped.emit(0))
    measure("đọc lại property (cache)", lambda: bridge.recentWorlds)
    measure("bản chơi đổi", lambda: bridge.instancesChanged.emit())
    measure("đứng yên", lambda: None)
    print(f"cảnh báo QML: {len(warnings)}")
    for message in warnings[:5]:
        print("  ", message.split("/qml/")[-1][:160])
    return 0


if __name__ == "__main__":
    sys.exit(main())
