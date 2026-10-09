"""Server catalog and settings work stays off the Qt event loop."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import Launcher, ServerGateway, ServerProperties
from nostalgia.errors import NostalgiaError, ServerError
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.game_log import GameLogFeed
from nostalgia.ui.server_results import ServerResults


class ServerBridge(ServerResults):
    def __init__(
        self,
        launcher: Launcher,
        gateway: ServerGateway | None = None,
        *,
        enabled: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._enabled, self._access = enabled, False
        self._access_pending, self._access_requested = False, False
        self._manager = launcher.make_server_manager(gateway if enabled else None)
        self._note = "Server chạy trên máy bạn · Pro / Max / Ultimate · Không kèm VPS"
        self._servers, self._selected = [], {}
        self._game_versions, self._builds = [], []
        self._projects, self._content_versions, self._installed = [], [], []
        self._config_files, self._config_text = [], ""
        self._cancel = CancelToken()
        self._feed = GameLogFeed(self)
        self._result.connect(self._apply)
        self.failed.connect(self._failure)
        self.busyChanged.connect(self._check_when_ready)
        self._poll = QTimer(self)
        self._poll.setInterval(1000)
        self._poll.timeout.connect(self.changed.emit)
        self._poll.start()
        self._heartbeat = QTimer(self)
        self._heartbeat.setInterval(30_000)
        self._heartbeat.timeout.connect(self._tick)
        self._heartbeat.start()
        try:
            self._refresh()
        except NostalgiaError as error:
            self._note = str(error)

    def set_gateway(self, gateway: ServerGateway | None) -> None:
        self._access = False
        self.next_generation()
        self._cancel.cancel()
        self._manager.set_gateway(gateway if self._enabled else None)
        self.changed.emit()
        if self._manager.running_id:
            self.stop()
        if self._access_requested:
            self.checkAccess()

    def _work(self, operation: Callable[[], None], activity: str) -> None:
        if not self.busy:
            self._job_generation = self.next_generation()
            self.run_in_background(operation, activity)

    def _publish(self, result_kind: str, payload: object) -> None:
        self._result.emit(self._job_generation, result_kind, payload)

    def _tick(self) -> None:
        if not self._manager.running_id:
            self._feed.end_session()
        self.changed.emit()

    @Slot()
    def stop(self) -> None:
        self._cancel.cancel()
        self._work(self._manager.stop, "Đang lưu thế giới và dừng server…")

    @Slot(str)
    def _failure(self, message: str) -> None:
        self._note = message
        self.changed.emit()

    @Slot()
    def refreshAccess(self) -> None:
        if self._access_requested:
            self.checkAccess()

    @Slot()
    def checkAccess(self) -> None:
        if not self._enabled:
            return
        self._access_pending, self._access_requested = True, True
        QTimer.singleShot(0, self._check_when_ready)

    @Slot()
    def _check_when_ready(self) -> None:
        if not self._access_pending or self.busy:
            return
        self._access_pending = False
        self._access = False
        self._note = "Đang kiểm tra quyền host của tài khoản Google…"
        self.changed.emit()

        def work() -> None:
            access = self._manager.authorize()
            self._publish("access", access.plan_name)

        self._work(work, "Đang xác minh gói của tài khoản Google…")

    @Slot(str)
    def loadVersions(self, engine_id: str) -> None:
        self._game_versions, self._builds = [], []
        self.changed.emit()
        self._work(
            lambda: self._publish("versions", self._manager.versions(engine_id)),
            "Đang tải phiên bản server…",
        )

    @Slot(str, str)
    def loadBuilds(self, engine_id: str, game_version: str) -> None:
        self._builds = []
        self.changed.emit()
        self._work(
            lambda: self._publish("builds", self._manager.builds(engine_id, game_version)),
            "Đang lấy bản server chính thức…",
        )

    @Slot(str, str, str, str)
    def create(self, display_name: str, engine_id: str, game_version: str, build_id: str) -> None:
        if self.busy:
            return
        self._cancel = CancelToken()

        def work() -> None:
            server = self._manager.install(
                display_name, engine_id, game_version, build_id, self._cancel
            )
            self._publish("created", server.server_id)

        self._work(work, "Đang tải và kiểm tra server…")

    @Slot(str)
    def select(self, server_id: str) -> None:
        def work() -> None:
            self._publish(
                "selection",
                self._manager.selection(server_id),
            )

        self._work(work, "Đang đọc server…")

    @Slot(dict, int, str, bool)
    def saveSettings(
        self, values: dict[str, Any], heap_megabytes: int, java_binary: str, eula: bool
    ) -> None:
        server_id = str(self._selected.get("server_id", ""))
        properties = ServerProperties(tuple((k, str(v)) for k, v in values.items()), eula)

        def work() -> None:
            self._manager.save_settings(server_id, properties, heap_megabytes, java_binary.strip())
            self._publish("selection", self._manager.selection(server_id))
            self._publish("saved", None)

        self._work(work, "Đang lưu cấu hình server…")

    @Slot(str)
    def openFolder(self, server_id: str) -> None:
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._manager.directory(server_id))))
        except ServerError as error:
            self.failed.emit(str(error))

    @Slot(str)
    def trash(self, server_id: str) -> None:
        def work() -> None:
            self._manager.trash(server_id)
            self._publish("refresh", None)

        self._work(work, "Đang chuyển server vào servers/.trash…")
