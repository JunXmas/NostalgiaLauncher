"""Cầu nối cho trang MOD và TÀI NGUYÊN: tìm trên Modrinth, cài, và quản lý file đã cài.

Kết quả tìm kiếm có thế hệ: gõ nhanh hai từ khoá thì chỉ kết quả của từ khoá sau được hiện,
dù mạng trả kết quả của từ khoá trước muộn hơn.
"""

from __future__ import annotations

import threading
from typing import Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import ContentTarget, Launcher
from nostalgia.content.model import ContentKind, Project, SortOrder
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.worker import WorkerBridge


class ContentBridge(WorkerBridge):
    targetChanged = Signal()
    resultsChanged = Signal()
    installedChanged = Signal()
    searchingChanged = Signal()
    installFinished = Signal(str)

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._main_bridge = main_bridge
        self._target: ContentTarget | None = None
        self._results: list[Project] = []
        self._total_hits = 0
        self._searching = False
        self._installed: list[dict[str, Any]] = []
        self._installing: set[str] = set()
        self._results_lock = threading.Lock()
        self._last_query: tuple[ContentKind, str, SortOrder] = ("mod", "", "relevance")

    # ----- bản chơi đang chọn -----

    @Property(str, notify=targetChanged)
    def instanceId(self) -> str:
        return self._target.instance_id if self._target else ""

    @Property(str, notify=targetChanged)
    def gameVersion(self) -> str:
        return self._target.game_version if self._target else ""

    @Property(str, notify=targetChanged)
    def loaderKind(self) -> str:
        return self._target.loader_kind if self._target else ""

    @Slot(str)
    def selectInstance(self, instance_id: str) -> None:
        """Đọc đĩa (nhanh) nên làm ngay; xoá kết quả cũ vì chúng thuộc bản chơi khác."""
        self._target = self._launcher.describe_content_target(instance_id) if instance_id else None
        self._results, self._total_hits = [], 0
        self._installed = []
        self.targetChanged.emit()
        self.resultsChanged.emit()
        self.installedChanged.emit()

    # ----- tìm kiếm -----

    @Property(list, notify=resultsChanged)
    def results(self) -> list[dict[str, Any]]:
        installed_ids = {row["projectId"] for row in self._installed if row["projectId"]}
        return [
            {
                "projectId": project.project_id,
                "title": project.title,
                "author": project.author,
                "description": project.description,
                "iconUrl": project.icon_url,
                "downloads": project.downloads,
                "follows": project.follows,
                "loaders": list(project.loaders),
                "installed": project.project_id in installed_ids,
                "installing": project.project_id in self._installing,
            }
            for project in self._results
        ]

    @Property(int, notify=resultsChanged)
    def totalHits(self) -> int:
        return self._total_hits

    @Property(bool, notify=resultsChanged)
    def hasMore(self) -> bool:
        return len(self._results) < self._total_hits

    @Property(bool, notify=searchingChanged)
    def searching(self) -> bool:
        return self._searching

    @Slot(str, str, str)
    def search(self, content_kind: str, query: str, sort: str) -> None:
        self._last_query = (
            cast(ContentKind, content_kind),
            query.strip(),
            cast(SortOrder, sort or "relevance"),
        )
        self._fetch_page(offset=0)

    @Slot()
    def loadMore(self) -> None:
        if self.hasMore and not self._searching:
            self._fetch_page(offset=len(self._results))

    def _fetch_page(self, *, offset: int) -> None:
        target = self._target
        if target is None:
            return
        content_kind, query, sort = self._last_query
        generation = self.next_generation()
        self._set_searching(True)

        def work() -> None:
            try:
                page = self._launcher.search_content(
                    target, content_kind, query=query, sort=sort, offset=offset
                )
                if not self.is_current(generation):
                    return
                with self._results_lock:
                    kept = self._results if offset else []
                    known = {project.project_id for project in kept}
                    fresh = [hit for hit in page.hits if hit.project_id not in known]
                    self._results = kept + fresh
                    self._total_hits = page.total_hits
                self.resultsChanged.emit()
            finally:
                if self.is_current(generation):
                    self._set_searching(False)

        self.run_in_background(work)

    def _set_searching(self, searching: bool) -> None:
        if self._searching != searching:
            self._searching = searching
            self.searchingChanged.emit()

    # ----- cài và quản lý -----

    @Slot(str)
    def install(self, project_id: str) -> None:
        target = self._target
        project = next((p for p in self._results if p.project_id == project_id), None)
        if target is None or project is None or project_id in self._installing:
            return
        self._installing.add(project_id)
        self.resultsChanged.emit()

        def work() -> None:
            try:
                self._launcher.install_content(
                    target, project, on_progress=self._main_bridge.report_progress
                )
                self._reload_installed(project.content_kind)
                self.installFinished.emit(project.title)
            finally:
                self._installing.discard(project_id)
                self.resultsChanged.emit()

        self.run_in_background(work)

    @Property(list, notify=installedChanged)
    def installed(self) -> list[dict[str, Any]]:
        return self._installed

    @Slot(str)
    def refreshInstalled(self, content_kind: str) -> None:
        """Đọc đĩa, không chạm mạng — làm ngay, không cần luồng nền."""
        self._reload_installed(cast(ContentKind, content_kind))

    @Slot(str, str, bool)
    def setEnabled(self, content_kind: str, file_name: str, enabled: bool) -> None:
        if self._target is None:
            return
        chosen_kind = cast(ContentKind, content_kind)
        self._launcher.set_content_enabled(self._target, chosen_kind, file_name, enabled)
        self._reload_installed(chosen_kind)

    @Slot(str, str)
    def remove(self, content_kind: str, file_name: str) -> None:
        if self._target is None:
            return
        chosen_kind = cast(ContentKind, content_kind)
        self._launcher.remove_content(self._target, chosen_kind, file_name)
        self._reload_installed(chosen_kind)
        self.resultsChanged.emit()

    def _reload_installed(self, content_kind: ContentKind) -> None:
        if self._target is None:
            return
        self._installed = [
            {
                "fileName": installed.file_name,
                "label": installed.label,
                "fileSize": installed.file_size,
                "enabled": installed.enabled,
                "projectId": installed.project_id,
                "versionNumber": installed.version_number,
                "contentKind": installed.content_kind,
            }
            for installed in self._launcher.list_installed_content(self._target, content_kind)
        ]
        self.installedChanged.emit()
