"""Cầu nối cho trang Nhập bản chơi: quét launcher, nhập .mrpack, nhập từ launcher, đồng bộ Rooms.

Tách khỏi các bridge khác cho mỗi file ngắn; cùng một QObject nhìn từ QML.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Found, Launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import slugify
from nostalgia.ui.worker import WorkerBridge, local_path

logger = logging.getLogger(__name__)


class ImportBridge(WorkerBridge):
    """Cầu nối cho dialog nhập bản chơi."""

    scanDone = Signal(list)
    importProgress = Signal(int, int)
    importDone = Signal(str)
    importError = Signal(str)

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self._found_list: list[Found] = []

    @Property(list, notify=scanDone)
    def scanResults(self) -> list[dict[str, Any]]:
        """Kết quả quét dạng dict cho QML."""
        return [
            {
                "launcher": found.launcher,
                "instanceName": found.instance_name,
                "gameDir": str(found.game_dir),
                "gameVersion": found.game_version,
                "loaderKind": found.loader_kind,
            }
            for found in self._found_list
        ]

    @Slot()
    def scanLaunchers(self) -> None:
        """Quét launcher khác, không chặn luồng giao diện."""

        def work() -> None:
            results = self._launcher.scan_external_launchers()
            self._found_list = results
            self.scanDone.emit(self.scanResults)

        self.run_in_background(work, "Đang quét launcher trên máy...")

    @Slot(str, str, str)
    def importMrpackFile(self, file_url: str, display_label: str, game_dir_url: str) -> None:
        """Nhập modpack từ file .mrpack trên máy."""
        pack_path = Path(local_path(file_url))
        game_dir_override = local_path(game_dir_url)
        if not pack_path.is_file():
            self.importError.emit(f"Không thấy file {pack_path}")
            return

        def work() -> None:
            taken = {i.instance_id for i in self._launcher.list_instances()}
            final_label = display_label.strip() or pack_path.stem
            instance = self._launcher.install_modpack_file(
                pack_path,
                slugify(final_label, taken),
                final_label,
                game_dir_override=game_dir_override,
                on_progress=self._main_bridge.report_progress,
            )
            self._main_bridge.instancesChanged.emit()
            self.importDone.emit(instance.instance_id)

        self.run_in_background(work, f"Nhập modpack {pack_path.name}")

    @Slot(int, str)
    def importFromLauncher(self, index: int, display_name: str) -> None:
        """Nhập instance từ launcher khác (index trong danh sách đã quét)."""
        if index < 0 or index >= len(self._found_list):
            self.importError.emit("Instance không hợp lệ")
            return
        found = self._found_list[index]

        def work() -> None:
            taken = {i.instance_id for i in self._launcher.list_instances()}
            display_label = display_name.strip() or found.instance_name
            instance = self._launcher.import_from_launcher(
                found,
                slugify(display_label, taken),
                display_label,
                on_progress=self._main_bridge.report_progress,
            )
            self._main_bridge.instancesChanged.emit()
            self.importDone.emit(instance.instance_id)

        self.run_in_background(work, f"Nhập {found.instance_name} từ {found.launcher}")
