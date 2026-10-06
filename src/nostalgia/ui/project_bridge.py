"""Cầu nối popup dự án; kết quả về muộn không được thay nội dung dự án mới."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.content.model import Project
from nostalgia.errors import NostalgiaError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.content_bridge import ContentBridge
from nostalgia.ui.project_catalog import (
    ProjectCatalog,
    build_content_targets,
    fetch_project_catalog,
    resolve_about_text,
)
from nostalgia.ui.project_install_bridge import ProjectInstallBridge
from nostalgia.ui.project_model import ProjectListModel


class ProjectBridge(ProjectInstallBridge):
    detailsChanged = Signal()
    opened = Signal()
    _arrived = Signal(int, object, str)

    def __init__(
        self,
        launcher: Launcher,
        main_bridge: LauncherBridge,
        content_bridge: ContentBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(launcher, main_bridge, content_bridge, parent)
        self._project = None
        self._catalog = None
        self._about = ""
        self._loading = False
        self._error = ""
        self._arrived.connect(self._apply_catalog)
        self.failed.connect(self._report_error)
        self.installed.connect(self._clear_error)

    @Property(dict, notify=detailsChanged)
    def details(self) -> dict[str, Any]:
        project, project_catalog = self._project, self._catalog
        return {
            "projectId": project.project_id if project else "",
            "title": project.title if project else "",
            "author": project.author if project else "",
            "iconUrl": project.icon_url if project else "",
            "description": project.description if project else "",
            "contentKind": project.content_kind if project else "",
            "source": project.source if project else "",
            "about": self._about,
            "websiteUrl": project_catalog.details.website_url if project_catalog else "",
            "notice": project_catalog.notice if project_catalog else "",
            "loading": self._loading,
            "error": self._error,
            "versions": [
                {
                    "versionId": release.version_id,
                    "number": release.version_number,
                    "type": release.version_type,
                    "gameVersions": list(release.game_versions),
                    "loaders": list(release.loaders),
                    "date": release.date_published[:10],
                }
                for release in project_catalog.versions
            ]
            if project_catalog
            else [],
            "targets": [
                {
                    "instanceId": target.instance_id,
                    "gameVersion": target.game_version,
                    "loaderKind": target.loader_kind,
                }
                for target in project_catalog.targets
            ]
            if project_catalog
            else [],
        }

    @Slot(str)
    def openProject(self, project_id: str) -> None:
        if self._installing:
            return
        project = next(
            (
                p
                for p in cast(ProjectListModel, self._content_bridge.resultsModel).projects
                if p.project_id == project_id
            ),
            None,
        )
        if project is None:
            return
        self._fetch_project(project)

    def _fetch_project(self, project: Project) -> None:
        self._project = project
        self._catalog = None
        self._about = project.description
        self._error = ""
        self._loading = True
        generation = self.next_generation()
        self.detailsChanged.emit()
        self.opened.emit()

        def work() -> None:
            try:
                project_catalog = fetch_project_catalog(self._launcher, project)
            except NostalgiaError as error:
                self._arrived.emit(generation, None, str(error))
            except Exception as error:
                self._arrived.emit(generation, None, f"Không tải được dự án: {error}")
            else:
                self._arrived.emit(generation, project_catalog, "")

        self.run_in_background(work, f"Giới thiệu {project.title}")

    @Slot()
    def reload(self) -> None:
        if self._project and not self._installing:
            self._fetch_project(self._project)

    @Slot()
    def refreshTargets(self) -> None:
        if self._catalog:
            self._catalog = replace(self._catalog, targets=build_content_targets(self._launcher))
            self.detailsChanged.emit()

    @Slot(str)
    def _clear_error(self, _title: str) -> None:
        self._report_error("")

    @Slot(int, object, str)
    def _apply_catalog(self, generation: int, payload: object, error: str) -> None:
        if not self.is_current(generation):
            return
        self._catalog = cast(ProjectCatalog | None, payload)
        self._error = error
        self._loading = False
        if self._catalog:
            self._about = resolve_about_text(self._catalog.details) or self._about
        self.detailsChanged.emit()

    @Slot(str)
    def _report_error(self, message: str) -> None:
        self._error = message
        self._loading = False
        self.detailsChanged.emit()
