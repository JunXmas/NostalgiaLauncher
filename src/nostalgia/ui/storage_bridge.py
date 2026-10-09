"""Xuất modpack, xóa và khôi phục dữ liệu cũ qua façade; tác vụ nặng chạy nền."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import Launcher
from nostalgia.errors import InstanceError, NostalgiaError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.worker import WorkerBridge, local_path


class StorageBridge(WorkerBridge):
    entriesChanged = Signal()
    completed = Signal(str)
    modpackExported = Signal(str)

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self.busyChanged.connect(self._sync_storage_busy)

    @Slot()
    def _sync_storage_busy(self) -> None:
        self._main_bridge.setStorageBusy(bool(self.busy))

    def run_in_background(self, work: Callable[[], None], activity: str = "Đang xử lý...") -> None:
        if self.busy:
            self.failed.emit("hãy đợi thao tác dữ liệu hiện tại hoàn tất")
            return
        super().run_in_background(work, activity)

    @Property(list, notify=entriesChanged)
    def backups(self) -> list[dict[str, Any]]:
        return [
            {
                "path": str(record.path),
                "label": record.display_name,
                "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(record.created_at)),
                "size": f"{record.size_bytes / 1024**2:.1f} MiB",
            }
            for record in self._launcher.list_instance_backups()
        ]

    @Property(list, notify=entriesChanged)
    def trash(self) -> list[dict[str, Any]]:
        return [
            {"trashId": record.trash_id, "label": record.display_name}
            for record in self._launcher.list_trashed_instances()
        ]

    def _require_stopped(self) -> None:
        if self._main_bridge.gameRunning or self._main_bridge.busy:
            raise InstanceError("hãy dừng game trước khi đóng gói hoặc thay đổi dữ liệu")

    @Slot(str, str, str, bool)
    def exportModpack(
        self,
        instance_id: str,
        file_url: str,
        archive_format: str,
        include_worlds: bool,
    ) -> None:
        def work() -> None:
            self._require_stopped()
            exported = self._launcher.export_instance_modpack(
                instance_id,
                Path(local_path(file_url)),
                archive_format,
                include_worlds=include_worlds,
                overwrite=True,
            )
            self.modpackExported.emit(str(exported.path))
            self._changed(f"Đã xuất {exported.file_count} file thành {archive_format.upper()}")

        self.run_in_background(work, "Đang đóng gói modpack…")

    @Slot(str, str, result=str)
    def suggestedExportFile(self, instance_id: str, archive_format: str) -> str:
        folder = self._launcher.paths.data_dir / "exports"
        folder.mkdir(parents=True, exist_ok=True)
        # Chỉ dùng mã đã đăng ký, không ghép đường dẫn từ một tên nhập tự do.
        if archive_format not in ("mrpack", "zip") or not any(
            instance.instance_id == instance_id for instance in self._launcher.list_instances()
        ):
            return ""
        filename = instance_id + "-" + time.strftime("%Y%m%d-%H%M%S") + "." + archive_format
        return (folder / filename).as_uri()

    @Slot()
    @Slot(str)
    def openExportsFolder(self, file_path: str = "") -> None:
        folder = (
            Path(local_path(file_path)).parent
            if file_path
            else self._launcher.paths.data_dir / "exports"
        )
        if not file_path:
            folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot(str)
    @Slot(str, bool)
    def deletePermanently(self, instance_id: str, delete_external: bool = False) -> None:
        def work() -> None:
            self._require_stopped()
            self._launcher.delete_instance(instance_id, delete_external=delete_external)
            self._changed("Đã xóa vĩnh viễn bản chơi")

        self.run_in_background(work, "Xóa vĩnh viễn bản chơi")

    @Slot(str)
    def purgeTrash(self, trash_id: str) -> None:
        def work() -> None:
            self._require_stopped()
            self._launcher.remove_trashed_instance(trash_id)
            self._changed("Đã xóa vĩnh viễn bản chơi trong thùng rác")

        self.run_in_background(work, "Xóa vĩnh viễn dữ liệu cũ")

    def _changed(self, message: str) -> None:
        self._main_bridge.announce_instances_changed()
        self.entriesChanged.emit()
        self.completed.emit(message)

    @Slot(str)
    def backup(self, instance_id: str) -> None:
        def work() -> None:
            self._require_stopped()
            self._launcher.backup_instance(instance_id)
            self._changed("Đã tạo bản sao lưu")

        self.run_in_background(work, "Sao lưu dữ liệu bản chơi")

    @Slot(str, str)
    def restoreBackup(self, path: str, instance_id: str) -> None:
        def work() -> None:
            self._require_stopped()
            restored = self._launcher.restore_instance_backup(Path(local_path(path)), instance_id)
            self._changed("Đã khôi phục thành bản chơi mới: " + restored.label)

        self.run_in_background(work, "Khôi phục dữ liệu bản chơi")

    @Slot(str)
    def moveToTrash(self, instance_id: str) -> None:
        def work() -> None:
            self._require_stopped()
            self._launcher.trash_instance(instance_id)
            self._changed("Đã chuyển vào thùng rác")

        self.run_in_background(work, "Chuyển bản chơi vào thùng rác")

    @Slot(str)
    def restoreTrash(self, trash_id: str) -> None:
        def work() -> None:
            self._require_stopped()
            self._launcher.restore_trashed_instance(trash_id)
            self._changed("Đã khôi phục bản chơi")

        self.run_in_background(work, "Khôi phục bản chơi từ thùng rác")

    @Slot(str, str, bool)
    def setOrganization(self, instance_id: str, group_name: str, favorite: bool) -> None:
        try:
            current = next(
                (i for i in self._launcher.list_instances() if i.instance_id == instance_id), None
            )
            if current is None:
                raise InstanceError("không còn bản chơi này")
            self._launcher.save_instance(
                replace(current, group_name=group_name.strip()[:60], favorite=favorite)
            )
            self._main_bridge.announce_instances_changed()
        except (NostalgiaError, OSError) as error:
            self.failed.emit(str(error))

    @Slot()
    def refresh(self) -> None:
        self.entriesChanged.emit()

    @Slot()
    def openBackupsFolder(self) -> None:
        folder = self._launcher.paths.data_dir / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
