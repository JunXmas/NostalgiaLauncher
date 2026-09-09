"""Phần bản chơi và tiến độ của cầu nối chính: danh sách bản chơi, thế giới chơi gần đây,
sửa/gỡ bản chơi.

Tách khỏi `bridge.py` để mỗi file dưới 200 dòng; QML vẫn thấy tất cả trên cùng một đối
tượng `bridge` vì `LauncherBridge` kế thừa lớp này.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import Instance, Launcher
from nostalgia.operations.progress import Progress
from nostalgia.ui.worker import WorkerBridge


class InstanceBridge(WorkerBridge):
    instancesChanged = Signal()
    progressChanged = Signal()
    recentWorldsChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._progress_text = ""
        self._progress_fraction = 0.0
        # Hàng cho QML giữ trong RAM: mỗi hàng kèm thống kê (đếm thế giới, mod trên đĩa), mà
        # trang chủ đọc `instances` ở nhiều binding — không quét đĩa lại cho từng binding.
        self._instance_rows: list[dict[str, Any]] | None = None
        # Thế giới gần đây cũng vậy: đọc level.dat chỉ khi bản chơi đổi hoặc game vừa tắt.
        self._recent_world_rows: list[dict[str, Any]] | None = None
        self.instancesChanged.connect(self._forget_instance_rows)
        self.instancesChanged.connect(self._forget_recent_worlds)

    def _forget_instance_rows(self) -> None:
        self._instance_rows = None

    def _forget_recent_worlds(self) -> None:
        self._recent_world_rows = None
        self.recentWorldsChanged.emit()

    @Property(list, notify=recentWorldsChanged)
    def recentWorlds(self) -> list[dict[str, Any]]:
        """Thế giới chơi gần nhất trên mọi bản chơi, mới nhất trước, tối đa 4 hàng."""
        if self._recent_world_rows is None:
            self._recent_world_rows = [
                {
                    "instanceId": world.instance_id,
                    "instanceLabel": world.instance_label,
                    "worldFolder": world.world_folder,
                    "worldName": world.world_name,
                    "lastPlayedAt": world.last_played_at,
                    "lastPlayedText": world.last_played_text,
                }
                for world in self._launcher.list_recent_worlds()
            ]
        return self._recent_world_rows

    @Property(list, notify=instancesChanged)
    def instances(self) -> list[dict[str, Any]]:
        """Danh sách bản chơi kèm thống kê, đã đổi sang dạng QML đọc được."""
        if self._instance_rows is None:
            self._instance_rows = [self._describe(i) for i in self._launcher.list_instances()]
        return self._instance_rows

    def _describe(self, instance: Instance) -> dict[str, Any]:
        stats = self._launcher.describe_instance_stats(instance.instance_id)
        return {
            "instanceId": instance.instance_id,
            "label": instance.label,
            "versionId": instance.version_id,
            "iconUrl": instance.icon_url,
            "maxHeapMegabytes": instance.max_heap_megabytes or 0,
            "windowWidth": instance.window_width or 0,
            "windowHeight": instance.window_height or 0,
            "gameDir": str(self._launcher.instance_game_dir(instance)),
            "customGameDir": bool(instance.game_dir_override),
            "playtimeText": stats.playtime_text,
            "launchCount": stats.play.launch_count,
            "lastPlayedAt": stats.play.last_played_at,
            "worldCount": stats.world_count,
            "modCount": stats.mod_count,
        }

    @Property(str, notify=progressChanged)
    def progressText(self) -> str:
        return self._progress_text

    @Property(float, notify=progressChanged)
    def progressFraction(self) -> float:
        return self._progress_fraction

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
        instance = next(
            (i for i in self._launcher.list_instances() if i.instance_id == instance_id), None
        )
        if instance is None:
            return
        folder = self._launcher.instance_game_dir(instance)
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
