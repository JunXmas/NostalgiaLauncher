"""Publish only the ready dedicated server's port; leave game LAN rooms independent."""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import ServerConnection
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.server_controller import ServerController
from nostalgia.ui.worker import WorkerBridge


class ServerRoomBridge(WorkerBridge):
    changed = Signal()
    _authorized = Signal(object)

    def __init__(
        self,
        servers: ServerController,
        multiplayer: MultiplayerBridge,
        synchronization: RoomSyncBridge,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._servers, self._multiplayer, self._sync = servers, multiplayer, synchronization
        self._connection: ServerConnection | None = None
        self._pending = False
        self._room_seen = False
        self._note = "Mở cho bạn bè sau khi console báo server sẵn sàng."
        self._authorized.connect(self._open)
        multiplayer.statusChanged.connect(self._room_changed)
        servers.changed.connect(self._server_changed)
        self.failed.connect(self._failed)

    @Property(bool, notify=changed)
    def active(self) -> bool:
        return self._connection is not None

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    @Slot()
    def open(self) -> None:
        if self.busy or self._servers.busy or self._multiplayer.active or self.active:
            return
        self._pending = True

        def work() -> None:
            self._authorized.emit(self._servers.domain_manager.room_connection())

        self.run_in_background(work, "Đang xác minh quyền và cổng server…")

    @Slot(object)
    def _open(self, result: object) -> None:
        connection = cast(ServerConnection, result)
        if not self._pending or self._servers.domain_manager.ready_id != connection.server_id:
            return
        self._pending = False
        if self._multiplayer.active:
            self._failed("Bạn đang ở phòng khác; rời phòng trước khi mở server cho bạn bè.")
            return
        self._connection = connection
        self._room_seen = False
        self._sync.set_host_ready(False)
        self._multiplayer.start_managed_hosting()
        self._note = "Đang mở kết nối tới server…"
        self.changed.emit()

    @Slot()
    def _room_changed(self) -> None:
        if not self._connection:
            return
        role = self._multiplayer.room_snapshot().role
        if role == "waiting_world":
            self._room_seen = True
            self._multiplayer.supplyLanPort(str(self._connection.port))
        elif role == "hosting":
            self._room_seen = True
            self._sync.set_host_ready(True)
            self._note = (
                "Đã mở cho bạn bè. Vào Bạn bè để gửi lời mời. Mod/hybrid cần client cùng modpack."
            )
        elif role == "idle" and self._room_seen:
            self.close()
        self.changed.emit()

    @Slot()
    def _server_changed(self) -> None:
        if self._connection and self._servers.domain_manager.ready_id != self._connection.server_id:
            self.close()

    @Slot(str)
    def _failed(self, message: str) -> None:
        self._pending = False
        self._note = message
        self.changed.emit()

    @Slot()
    def close(self) -> None:
        self._pending = False
        if self._connection:
            self._connection = None
            self._multiplayer.stop()
            self._sync.set_host_ready(True)
        self._note = "Đã đóng kết nối bạn bè. Server trên máy host có thể tiếp tục chạy."
        self.changed.emit()
