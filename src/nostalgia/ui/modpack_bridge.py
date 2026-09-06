"""Phần cài modpack của cầu nối nội dung: một thẻ modpack thành một bản chơi mới.

Tách khỏi `content_bridge.py` cho mỗi file ngắn; cùng một QObject nhìn từ QML.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal, Slot

from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import slugify
from nostalgia.ui.installed_bridge import InstalledContentBridge
from nostalgia.ui.project_model import ProjectListModel


class ModpackContentBridge(InstalledContentBridge):
    modpackInstalled = Signal(str)

    # Hợp đồng với lớp con (ContentBridge): nó sở hữu kết quả tìm, cờ đang cài, cầu nối chính
    # và tín hiệu vẽ lại cờ. Khai ở đây để mypy kiểm, không gán giá trị ở đây.
    _results_model: ProjectListModel
    _installing: set[str]
    _main_bridge: LauncherBridge
    _game_versions: list[str]
    _flagsDirty: Signal

    def _refresh_flags(self) -> None:
        raise NotImplementedError

    @Slot(str, str)
    def installModpack(self, project_id: str, display_name: str) -> None:
        """Modpack Modrinth thành một bản chơi mới; tên trống thì lấy tên pack."""
        project = next(
            (p for p in self._results_model.projects if p.project_id == project_id), None
        )
        if project is None or project.content_kind != "modpack" or project_id in self._installing:
            return
        self._installing.add(project_id)
        self._refresh_flags()

        def work() -> None:
            try:
                taken = {instance.instance_id for instance in self._launcher.list_instances()}
                display_label = display_name.strip() or project.title
                instance = self._launcher.install_modpack(
                    project,
                    slugify(display_label, taken),
                    display_label,
                    game_version=self._game_versions[0] if self._game_versions else "",
                    on_progress=self._main_bridge.report_progress,
                )
                self._main_bridge.instancesChanged.emit()
                self.modpackInstalled.emit(instance.instance_id)
            finally:
                self._installing.discard(project_id)
                self._flagsDirty.emit()

        self.run_in_background(work, f"Cài modpack {project.title} thành bản chơi")

    @Slot(str, str)
    def importModpackFile(self, file_url: str, display_name: str) -> None:
        """Modpack từ file trên máy (FileDialog trả URL file://). Tên trống thì lấy tên pack."""
        pack_path = Path(QUrl(file_url).toLocalFile() or file_url)
        if not pack_path.is_file():
            self.failed.emit(f"không thấy file {pack_path}")
            return

        def work() -> None:
            taken = {instance.instance_id for instance in self._launcher.list_instances()}
            display_label = display_name.strip() or pack_path.stem
            instance = self._launcher.install_modpack_file(
                pack_path,
                slugify(display_label, taken),
                display_name.strip(),
                on_progress=self._main_bridge.report_progress,
            )
            self._main_bridge.instancesChanged.emit()
            self.modpackInstalled.emit(instance.instance_id)

        self.run_in_background(work, f"Cài modpack {pack_path.name} thành bản chơi")
