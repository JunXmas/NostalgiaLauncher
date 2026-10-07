"""Apply domain results on the Qt thread and ignore results from a rotated session."""

from __future__ import annotations

from dataclasses import asdict
from typing import cast

from PySide6.QtCore import QTimer, Slot

from nostalgia.api import (
    ENGINES,
    InstalledServerContent,
    ServerArtifact,
    ServerContentVersion,
    ServerProject,
    ServerSelection,
)
from nostalgia.ui.server_state import ServerState


class ServerResults(ServerState):
    def _refresh(self) -> None:
        self._servers = [
            asdict(server)
            | {"engine_title": next(e.title for e in ENGINES if e.engine_id == server.engine_id)}
            for server in self._manager.list_servers()
        ]
        self.changed.emit()

    @Slot(int, str, object)
    def _apply(self, generation: int, result_kind: str, payload: object) -> None:
        if not self.is_current(generation):
            return
        if result_kind == "access":
            self._access = True
            self._note = cast(str, payload) + " · Có thể tạo và quản lý server trên máy bạn."
        elif result_kind == "versions":
            self._game_versions, self._builds = list(cast(tuple[str, ...], payload)), []
        elif result_kind == "builds":
            self._builds = [a.build_id for a in cast(tuple[ServerArtifact, ...], payload)]
        elif result_kind == "created":
            self._refresh()
            QTimer.singleShot(20, lambda: self.created.emit(cast(str, payload)))
        elif result_kind == "selection":
            selection = cast(ServerSelection, payload)
            server, properties = selection.server, selection.properties
            installed, configs = selection.installed, selection.config_files
            self._selected = asdict(server) | {
                "properties": dict(properties.values),
                "eula": properties.eula_accepted,
                "engine_title": next(e.title for e in ENGINES if e.engine_id == server.engine_id),
            }
            self._installed = [asdict(row) for row in installed]
            self._config_files = list(configs)
            self._projects, self._content_versions, self._config_text = [], [], ""
            self.selectionLoaded.emit()
        elif result_kind == "refresh":
            self._refresh()
        elif result_kind == "saved":
            self._note = "Đã lưu cấu hình. Thiết lập có hiệu lực ở lần khởi chạy tiếp theo."
        elif result_kind == "projects":
            self._projects, self._content_versions = (
                [asdict(row) for row in cast(tuple[ServerProject, ...], payload)],
                [],
            )
        elif result_kind == "contentVersions":
            self._content_versions = [
                asdict(row) for row in cast(tuple[ServerContentVersion, ...], payload)
            ]
        elif result_kind == "installed":
            self._installed = [
                asdict(row) for row in cast(tuple[InstalledServerContent, ...], payload)
            ]
            self.contentInstalled.emit()
        elif result_kind == "configText":
            self._config_text = cast(str, payload)
            self.configLoaded.emit()
        self.changed.emit()
