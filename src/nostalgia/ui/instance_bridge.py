"""Phần bản chơi và tiến độ của cầu nối chính: danh sách bản chơi, tải phiên bản, sửa/gỡ.

Tách khỏi `bridge.py` để mỗi file dưới 200 dòng; QML vẫn thấy tất cả trên cùng một đối
tượng `bridge` vì `LauncherBridge` kế thừa lớp này.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import Launcher
from nostalgia.operations.progress import Progress
from nostalgia.ui.worker import WorkerBridge


class InstanceBridge(WorkerBridge):
    instancesChanged = Signal()
    progressChanged = Signal()
    versionInstalled = Signal(str)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._progress_text = ""
        self._progress_fraction = 0.0

    @Property(list, notify=instancesChanged)
    def instances(self) -> list[dict[str, Any]]:
        """Danh sách bản chơi, đã đổi sang dạng QML đọc được."""
        return [
            {
                "instanceId": instance.instance_id,
                "label": instance.label,
                "versionId": instance.version_id,
                "iconUrl": instance.icon_url,
                "maxHeapMegabytes": instance.max_heap_megabytes or 0,
                "windowWidth": instance.window_width or 0,
                "windowHeight": instance.window_height or 0,
                "gameDir": str(self._launcher.paths.instance_dir(instance.instance_id)),
            }
            for instance in self._launcher.list_instances()
        ]

    @Property(list, notify=instancesChanged)
    def installedVersions(self) -> list[str]:
        """Các phiên bản đã tải về máy. Đọc đĩa, không chạm mạng."""
        return list(self._launcher.list_installed_versions())

    @Property(str, notify=progressChanged)
    def progressText(self) -> str:
        return self._progress_text

    @Property(float, notify=progressChanged)
    def progressFraction(self) -> float:
        return self._progress_fraction

    @Slot(str)
    def installVersion(self, version_id: str) -> None:
        """Tải một phiên bản ở luồng nền; giao diện vẫn vẽ được trong lúc đó."""

        def work() -> None:
            self._launcher.install_version(version_id, on_progress=self.report_progress)
            self.instancesChanged.emit()
            self.versionInstalled.emit(version_id)

        self.run_in_background(work, f"Cài Minecraft {version_id}")

    @Slot(str, str, int, int, int)
    def updateInstance(
        self, instance_id: str, display_name: str, max_heap: int, width: int, height: int
    ) -> None:
        """Sửa tên / RAM / kích thước cửa sổ. Ghi một file nhỏ: làm ngay, không cần luồng nền."""
        current = next(
            (i for i in self._launcher.list_instances() if i.instance_id == instance_id), None
        )
        if current is None:
            return
        self._launcher.save_instance(
            replace(
                current,
                display_name=display_name.strip(),
                max_heap_megabytes=max_heap or None,
                window_width=width or None,
                window_height=height or None,
            )
        )
        self.instancesChanged.emit()

    @Slot(str)
    def openInstanceFolder(self, instance_id: str) -> None:
        """Mở thư mục bản chơi bằng trình quản lý file của hệ điều hành."""
        folder = self._launcher.paths.instance_dir(instance_id)
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot(str)
    def removeInstance(self, instance_id: str) -> None:
        """Gỡ đăng ký bản chơi; thư mục thế giới vẫn còn nguyên trên đĩa."""

        def work() -> None:
            self._launcher.remove_instance(instance_id)
            self.instancesChanged.emit()

        self.run_in_background(work, f"Gỡ bản chơi {instance_id}")

    @Slot()
    def clearProgress(self) -> None:
        """Toast gọi khi mọi việc đã xong, để lần sau không hiện chữ tiến độ cũ."""
        self._progress_text = ""
        self._progress_fraction = 0.0
        self.progressChanged.emit()

    def report_progress(self, progress: Progress) -> None:
        self._progress_text = f"{progress.stage} {progress.done}/{progress.total}"
        self._progress_fraction = progress.fraction
        self.progressChanged.emit()
