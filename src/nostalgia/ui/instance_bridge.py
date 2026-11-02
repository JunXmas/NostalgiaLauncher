"""Phần bản chơi và tiến độ của cầu nối chính: danh sách bản chơi, nơi vào thẳng khi bấm Chơi
(thế giới, server), sửa/gỡ bản chơi.

Tách khỏi `bridge.py` để mỗi file dưới 200 dòng; QML vẫn thấy tất cả trên cùng một đối
tượng `bridge` vì `LauncherBridge` kế thừa lớp này.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import Instance, Launcher, NosClientConfig
from nostalgia.operations.progress import Progress
from nostalgia.ui.worker import WorkerBridge


class InstanceBridge(WorkerBridge):
    instancesChanged = Signal()
    storageBusyChanged = Signal()
    progressChanged = Signal()
    # Bấm Chơi: (mã bản chơi, thế giới, server, tab mở sẵn). Cả hai rỗng → QML mở game luôn.
    playChoicesReady = Signal(str, list, list, str)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._storage_busy = False
        self._progress_text = ""
        self._progress_fraction = 0.0
        # Hàng cho QML giữ trong RAM: mỗi hàng kèm thống kê (đếm thế giới, mod trên đĩa), mà
        # trang chủ đọc `instances` ở nhiều binding — không quét đĩa lại cho từng binding.
        self._instance_rows: list[dict[str, Any]] | None = None
        self.instancesChanged.connect(self._forget_instance_rows)

    @Property(bool, notify=storageBusyChanged)
    def storageBusy(self) -> bool:
        return self._storage_busy

    @Slot(bool)
    def setStorageBusy(self, busy: bool) -> None:
        self._storage_busy = busy
        self.storageBusyChanged.emit()

    @Slot()
    def announce_instances_changed(self) -> None:
        """Invalidate snapshots before QML property notifications read them."""
        self._instance_rows = None
        self.instancesChanged.emit()

    def _forget_instance_rows(self) -> None:
        self._instance_rows = None

    @Slot(str)
    def loadPlayChoices(self, instance_id: str) -> None:
        """Đọc thế giới + server của bản chơi ở luồng nền rồi phát `playChoicesReady`. Bản game
        không vào thẳng được nơi nào thì danh sách đó rỗng — chọn cũng chỉ mở game như cũ."""

        def work() -> None:
            choices = self._launcher.describe_play_choices(instance_id)
            worlds = choices.worlds if choices.quick_play.worlds else ()
            servers = choices.servers if choices.quick_play.servers else ()
            newest_world = worlds[0].last_played_at if worlds else -1
            server_first = bool(servers) and choices.servers_changed_at > newest_world
            self.playChoicesReady.emit(
                instance_id,
                [
                    {
                        "worldFolder": world.world_folder,
                        "worldName": world.world_name,
                        "lastPlayedAt": world.last_played_at,
                        "lastPlayedText": world.last_played_text,
                        "gameType": world.game_type,
                        "hardcore": world.hardcore,
                        "cheats": world.cheats,
                        "iconUrl": world.icon_url,
                    }
                    for world in worlds
                ],
                [
                    {"serverName": s.server_name, "address": s.address, "iconUrl": s.icon_url}
                    for s in servers
                ],
                "multiplayer" if server_first else "singleplayer",
            )

        self.run_in_background(work, f"Đọc thế giới của {instance_id}")

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
            "groupName": instance.group_name,
            "favorite": instance.favorite,
            "maxHeapMegabytes": instance.max_heap_megabytes or 0,
            "windowWidth": instance.window_width or 0,
            "windowHeight": instance.window_height or 0,
            "gameDir": str(self._launcher.instance_game_dir(instance)),
            "customGameDir": bool(instance.game_dir_override),
            "javaBinary": instance.java_binary_override,
            "playtimeText": stats.playtime_text,
            "launchCount": stats.play.launch_count,
            "lastPlayedAt": stats.play.last_played_at,
            "worldCount": stats.world_count,
            "modCount": stats.mod_count,
            "nosClientEnabled": instance.nos_client_enabled,
            # Bản Nos hiện tại chỉ dành cho Fabric 1.21.11; nơi khác không hiện công tắc.
            "nosClientSupported": instance.version_id.startswith("fabric-loader-")
            and instance.version_id.endswith("-1.21.11"),
        }

    def _find(self, instance_id: str) -> Instance | None:
        return next(
            (i for i in self._launcher.list_instances() if i.instance_id == instance_id), None
        )

    @Property(str, notify=progressChanged)
    def progressText(self) -> str:
        return self._progress_text

    @Property(float, notify=progressChanged)
    def progressFraction(self) -> float:
        return self._progress_fraction

    @Slot(str, str, int, int, int, str, result=bool)
    def updateInstance(
        self, instance_id: str, name: str, heap: int, width: int, height: int, java_binary: str = ""
    ) -> bool:
        """Sửa tên / RAM / cửa sổ / Java nâng cao (rỗng = tự chọn). Ghi một file nhỏ, làm ngay.

        Trả False, KHÔNG lưu gì, khi Java đã chọn không phải file — báo ngay trong hộp thay vì
        để tới lúc bấm Chơi mới vỡ. FileDialog trả URL file:///…; ô nhập tay là đường dẫn thường.
        """
        current = self._find(instance_id)
        path = QUrl(java_binary).toLocalFile() if java_binary.startswith("file:") else java_binary
        path = path.strip()
        if current is None or (path and not Path(path).is_file()):
            return False
        self._launcher.save_instance(
            replace(
                current,
                display_name=name.strip(),
                max_heap_megabytes=heap or None,
                window_width=width or None,
                window_height=height or None,
                java_binary_override=path,
            )
        )
        self.announce_instances_changed()
        return True

    @Slot(str)
    def openInstanceFolder(self, instance_id: str) -> None:
        """Mở thư mục bản chơi bằng trình quản lý file của hệ điều hành."""
        instance = self._find(instance_id)
        if instance is None:
            return
        folder = self._launcher.instance_game_dir(instance)
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot(str)
    def removeInstance(self, instance_id: str) -> None:
        """Xoá hẳn bản chơi khỏi danh sách và xóa toàn bộ thư mục game (không thể hoàn tác)."""

        def work() -> None:
            self._launcher.delete_instance(instance_id)
            self.announce_instances_changed()

        self.run_in_background(work, f"Xoá bản chơi {instance_id}")

    @Slot(str, bool)
    def toggleNosClient(self, instance_id: str, enabled: bool) -> None:
        """Bật/tắt Nos Client cho một bản chơi. Tải mod ở nền nếu bật."""
        current = self._find(instance_id)
        if current is None:
            return

        def work() -> None:
            self._launcher.toggle_nos_client(current, enabled)
            if enabled:
                self._launcher.prepare_nos_client(replace(current, nos_client_enabled=True))
            else:
                self._launcher.cleanup_nos_client(current)
            self.announce_instances_changed()

        self.run_in_background(work, f"{'Bật' if enabled else 'Tắt'} Nos Client cho {instance_id}")

    @Slot(str, bool, bool, bool, bool, bool, bool)
    def updateNosClientConfig(
        self,
        instance_id: str,
        coords: bool,
        direction: bool,
        day: bool,
        fps: bool,
        ping: bool,
        cps: bool,
    ) -> None:
        """Cập nhật cấu hình HUD của Nos Client. Ghi file nhỏ: làm ngay."""
        current = self._find(instance_id)
        if current is None:
            return
        config = NosClientConfig(
            coords=coords,
            direction=direction,
            day=day,
            fps=fps,
            ping=ping,
            cps=cps,
        )
        self._launcher.set_nos_client_config(current, config)
        self.announce_instances_changed()

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
