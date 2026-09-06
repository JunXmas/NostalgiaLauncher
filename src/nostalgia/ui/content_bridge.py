"""Cầu nối cho trang MOD và TÀI NGUYÊN: bộ lọc, tìm trên Modrinth, cài. Phần "đã cài" ở
`installed_bridge.py`.

Kết quả tìm kiếm có thế hệ: gõ nhanh hai từ khoá thì chỉ kết quả của từ khoá sau được hiện,
dù mạng trả kết quả của từ khoá trước muộn hơn.
"""

from __future__ import annotations

import threading
from typing import Any, cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.content.model import ContentKind, Project, SortOrder
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.installed_bridge import InstalledContentBridge


class ContentBridge(InstalledContentBridge):
    targetChanged = Signal()
    filtersChanged = Signal()
    resultsChanged = Signal()
    searchingChanged = Signal()
    installFinished = Signal(str)

    def __init__(
        self, launcher: Launcher, main_bridge: LauncherBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(launcher, parent)
        self._main_bridge = main_bridge
        # Cờ "đã cài" trên thẻ kết quả suy từ danh sách đã cài, nên đổi bên này thì vẽ lại bên kia.
        self.installedChanged.connect(self.resultsChanged)
        self._results: list[Project] = []
        self._total_hits = 0
        self._searching = False
        self._installing: set[str] = set()
        self._results_lock = threading.Lock()
        self._last_query: tuple[ContentKind, str, SortOrder] = ("mod", "", "relevance")
        # Bộ lọc của cột trái. Rỗng nghĩa là không lọc theo tiêu chí đó.
        self._loaders: list[str] = []
        self._game_versions: list[str] = []

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
        """Đọc đĩa (nhanh) nên làm ngay; bộ lọc nhảy về loader + phiên bản của bản chơi đó."""
        self._target = self._launcher.describe_content_target(instance_id) if instance_id else None
        self._results, self._total_hits = [], 0
        self._installed = []
        if self._target is not None:
            self._loaders = (
                [self._target.loader_kind] if self._target.loader_kind != "vanilla" else []
            )
            self._game_versions = [self._target.game_version]
        self.targetChanged.emit()
        self.filtersChanged.emit()
        self.resultsChanged.emit()
        self.installedChanged.emit()

    # ----- bộ lọc -----

    @Property(list, notify=filtersChanged)
    def selectedLoaders(self) -> list[str]:
        return list(self._loaders)

    @Property(list, notify=filtersChanged)
    def selectedGameVersions(self) -> list[str]:
        return list(self._game_versions)

    @Slot(str, bool)
    def setLoaderSelected(self, loader_name: str, selected: bool) -> None:
        self._loaders = _toggle(self._loaders, loader_name, selected)
        self.filtersChanged.emit()

    @Slot(str, bool)
    def setGameVersionSelected(self, game_version: str, selected: bool) -> None:
        self._game_versions = _toggle(self._game_versions, game_version, selected)
        self.filtersChanged.emit()

    @Slot()
    def clearGameVersions(self) -> None:
        self._game_versions = []
        self.filtersChanged.emit()

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
        """Duyệt được cả khi chưa có bản chơi; chỉ lúc cài mới cần một bản chơi đích."""
        target = self._target
        content_kind, query, sort = self._last_query
        loaders, game_versions = tuple(self._loaders), tuple(self._game_versions)
        generation = self.next_generation()
        self._set_searching(True)

        def work() -> None:
            try:
                page = self._launcher.search_content(
                    target,
                    content_kind,
                    query=query,
                    sort=sort,
                    offset=offset,
                    game_versions=game_versions,
                    loaders=loaders,
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

        self.run_in_background(work, "Tìm trên Modrinth")

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

        kind_label = {"mod": "mod", "resourcepack": "gói tài nguyên", "shader": "shader"}
        self.run_in_background(work, f"Cài {kind_label[project.content_kind]} {project.title}")


def _toggle(values: list[str], value: str, selected: bool) -> list[str]:
    without = [existing for existing in values if existing != value]
    return [*without, value] if selected else without
