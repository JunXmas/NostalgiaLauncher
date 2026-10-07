"""Run/console and content operations for the dedicated server bridge."""

from __future__ import annotations

from PySide6.QtCore import Slot

from nostalgia.api import ServerManager
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.server_bridge import ServerBridge


class ServerController(ServerBridge):
    @Slot()
    def clearContent(self) -> None:
        self._projects, self._content_versions = [], []
        self.changed.emit()

    @property
    def domain_manager(self) -> ServerManager:
        return self._manager

    @Slot(str)
    def start(self, server_id: str) -> None:
        if self.busy:
            return
        self._cancel = CancelToken()
        self._feed.reset()
        self._feed.begin_session()

        def work() -> None:
            self._manager.start(server_id, self._feed.receive, self._cancel)
            self._publish("refresh", None)

        self._work(work, "Đang chuẩn bị Java và khởi chạy server…")

    @Slot(str)
    def command(self, text: str) -> None:
        self._work(lambda: self._manager.command(text), "Đang gửi lệnh console…")

    @Slot()
    def cancel(self) -> None:
        self._cancel.cancel()

    @Slot(str, str, str)
    def search(self, source: str, content_kind: str, query: str) -> None:
        server_id = str(self._selected.get("server_id", ""))
        self._work(
            lambda: self._publish(
                "projects", self._manager.search_content(server_id, source, content_kind, query)
            ),
            "Đang tìm plugin/mod tương thích…",
        )

    @Slot(str, str, str)
    def loadContentVersions(self, source: str, content_kind: str, project_id: str) -> None:
        server_id = str(self._selected.get("server_id", ""))
        self._work(
            lambda: self._publish(
                "contentVersions",
                self._manager.content_versions(server_id, source, content_kind, project_id),
            ),
            "Đang kiểm tra phiên bản plugin/mod…",
        )

    @Slot(str, str, str, str)
    def installContent(
        self, source: str, content_kind: str, project_id: str, version_id: str
    ) -> None:
        if self.busy:
            return
        server_id = str(self._selected.get("server_id", ""))
        self._cancel = CancelToken()

        def work() -> None:
            self._manager.install_content(
                server_id, source, content_kind, project_id, version_id, self._cancel
            )
            self._publish("installed", self._manager.installed_content(server_id))

        self._work(work, "Đang cài nội dung và dependency tương thích…")

    @Slot(str, str)
    def removeContent(self, content_kind: str, file_name: str) -> None:
        server_id = str(self._selected.get("server_id", ""))

        def work() -> None:
            self._manager.remove_content(server_id, content_kind, file_name)
            self._publish("installed", self._manager.installed_content(server_id))

        self._work(work, "Đang gỡ nội dung vào .nostalgia/removed…")

    @Slot(str)
    def readConfig(self, relative_path: str) -> None:
        server_id = str(self._selected.get("server_id", ""))
        self._work(
            lambda: self._publish(
                "configText", self._manager.read_config(server_id, relative_path)
            ),
            "Đang đọc cấu hình…",
        )

    @Slot(str, str)
    def saveConfig(self, relative_path: str, text: str) -> None:
        server_id = str(self._selected.get("server_id", ""))

        def work() -> None:
            self._manager.save_config(server_id, relative_path, text)
            self._publish("saved", None)

        self._work(work, "Đang lưu file cấu hình…")

    @Slot()
    def shutdown(self) -> None:
        self._poll.stop()
        self._heartbeat.stop()
        self._cancel.cancel()
        self._manager.shutdown()
        self._feed.end_session()
