"""Cầu nối cho hộp thoại tạo bản chơi: danh mục phiên bản, loader Fabric, và tạo + cài.

Mã bản chơi sinh từ tên hiển thị (`Sinh tồn vui` -> `sinh-ton-vui`), thêm hậu tố số nếu
trùng — người dùng không phải học luật đặt tên thư mục.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Instance, Launcher
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.worker import WorkerBridge


def slugify(display_name: str, taken: set[str]) -> str:
    """Mã hợp lệ theo `INSTANCE_ID_PATTERN`, duy nhất trong `taken`."""
    ascii_text = unicodedata.normalize("NFKD", display_name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_text).strip("-._").lower()[:60] or "ban-choi"
    if base[0] in "._-":
        base = "b" + base
    candidate, counter = base, 2
    while candidate in taken:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


class CatalogBridge(WorkerBridge):
    releasedVersionsChanged = Signal()
    fabricLoadersChanged = Signal()
    created = Signal(str)

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self._released: list[dict[str, Any]] = []
        self._fabric_loaders: list[dict[str, Any]] = []

    @Property(list, notify=releasedVersionsChanged)
    def releasedVersions(self) -> list[dict[str, Any]]:
        return self._released

    @Property(list, notify=fabricLoadersChanged)
    def fabricLoaders(self) -> list[dict[str, Any]]:
        return self._fabric_loaders

    @Slot()
    def loadReleasedVersions(self) -> None:
        """Danh mục bản chính thức của Mojang, mới nhất đứng đầu. Chạm mạng, chạy nền."""
        generation = self.next_generation()

        def work() -> None:
            released = self._launcher.list_released_versions(limit=500)
            if not self.is_current(generation):
                return
            self._released = [
                {
                    "versionId": released_version.version_id,
                    "major": _major(released_version.version_id),
                }
                for released_version in released
            ]
            self.releasedVersionsChanged.emit()

        self.run_in_background(work)

    @Slot(str)
    def loadFabricLoaders(self, game_version: str) -> None:
        generation = self.next_generation()

        def work() -> None:
            loaders = self._launcher.list_fabric_loader_versions(game_version)
            if not self.is_current(generation):
                return
            self._fabric_loaders = [
                {"loaderVersion": loader_version.loader_version, "stable": loader_version.stable}
                for loader_version in loaders
            ]
            self.fabricLoadersChanged.emit()

        self.run_in_background(work)

    @Slot(str, str, str, str, int)
    def createInstance(
        self,
        display_name: str,
        game_version: str,
        loader_kind: str,
        loader_version: str,
        max_heap_megabytes: int,
    ) -> None:
        """Cài phiên bản (và Fabric nếu chọn) rồi đăng ký bản chơi. Chạm mạng, chạy nền."""

        def work() -> None:
            report_progress = self._main_bridge.report_progress
            if loader_kind == "fabric":
                report = self._launcher.install_fabric(
                    game_version, loader_version or None, on_progress=report_progress
                )
                version_id = report.version_meta.version_id
            else:
                self._launcher.install_version(game_version, on_progress=report_progress)
                version_id = game_version
            taken = {instance.instance_id for instance in self._launcher.list_instances()}
            instance = Instance(
                instance_id=slugify(display_name, taken),
                version_id=version_id,
                display_name=display_name.strip(),
                max_heap_megabytes=max_heap_megabytes or None,
            )
            self._launcher.create_instance(instance)
            self._main_bridge.instancesChanged.emit()
            self.created.emit(instance.instance_id)

        self.run_in_background(work)


def _major(version_id: str) -> str:
    """`1.20.1` -> `1.20`; giữ nguyên nếu không theo mẫu."""
    parts = version_id.split(".")
    return ".".join(parts[:2]) if len(parts) >= 2 and parts[0].isdigit() else version_id
