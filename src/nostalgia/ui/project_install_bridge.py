"""Cài đúng bản phát hành đã chọn trong popup, độc lập với các bộ lọc tìm kiếm."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.content.model import Project
from nostalgia.errors import ContentError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.catalog_bridge import slugify
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.project_catalog import ProjectCatalog
from nostalgia.ui.worker import WorkerBridge


class ProjectInstallBridge(WorkerBridge):
    installingChanged = Signal()
    installed = Signal(str)
    _ended = Signal()
    _project: Project | None
    _catalog: ProjectCatalog | None

    def __init__(
        self,
        launcher: Launcher,
        main_bridge: LauncherBridge,
        content_bridge: ContentBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self._content_bridge = content_bridge
        self._installing = False
        self._ended.connect(self._finish_install)
        self.installed.connect(self._refresh_installed)

    @Slot(str)
    def _refresh_installed(self, title: str) -> None:
        if self._project and self._project.content_kind != "modpack":
            self._content_bridge.refreshInstalled(self._project.content_kind)
            self._content_bridge.installFinished.emit(title)

    @Property(bool, notify=installingChanged)
    def installing(self) -> bool:
        return self._installing

    @Slot()
    def _finish_install(self) -> None:
        self._installing = False
        self.installingChanged.emit()

    @Slot(str, str, str, str)
    def installVersion(
        self,
        version_id: str,
        game_version: str,
        instance_id: str,
        display_label: str,
    ) -> None:
        project, project_catalog = self._project, self._catalog
        if self._installing or project is None or project_catalog is None:
            return
        if cast(bool, self._content_bridge.busy):
            self.failed.emit("Đợi tác vụ thư viện hiện tại hoàn tất rồi thử lại.")
            return
        chosen = next((v for v in project_catalog.versions if v.version_id == version_id), None)
        if chosen is None or game_version not in chosen.game_versions:
            self.failed.emit("Phiên bản đã chọn không hỗ trợ Minecraft này.")
            return
        self._installing = True
        self.installingChanged.emit()

        def work() -> None:
            try:
                if project.content_kind == "modpack":
                    taken = {instance.instance_id for instance in self._launcher.list_instances()}
                    final_label = display_label.strip() or project.title
                    self._launcher.install_modpack(
                        project,
                        slugify(final_label, taken),
                        final_label,
                        game_version=game_version,
                        version_id=version_id,
                        on_progress=self._main_bridge.report_progress,
                    )
                    self._main_bridge.announce_instances_changed()
                else:
                    target = self._launcher.describe_content_target(instance_id)
                    if target.game_version != game_version or not chosen.supports(
                        target.game_version,
                        target.loader_kind,
                        project.content_kind,
                    ):
                        raise ContentError("selected instance is incompatible with this version")
                    self._launcher.install_content(
                        target,
                        project,
                        version_id=version_id,
                        on_progress=self._main_bridge.report_progress,
                    )
                self.installed.emit(project.title)
            finally:
                self._ended.emit()

        self.run_in_background(work, f"Cài {project.title} · {chosen.version_number}")
