"""Đồng bộ theo phòng: khách miễn phí, host được backend kiểm Plus ở từng request."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from nostalgia.api import Launcher, RoomSyncGateway, SyncManifest
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.worker import WorkerBridge


class RoomSyncBridge(WorkerBridge):
    stateChanged = Signal()
    _offerArrived = Signal(object, int)
    _completed = Signal(str, str, int)

    def __init__(
        self,
        launcher: Launcher,
        launcher_bridge: LauncherBridge,
        multiplayer_bridge: MultiplayerBridge,
        gateway: RoomSyncGateway | None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._launcher_bridge = launcher_bridge
        self._multiplayer = multiplayer_bridge
        self._gateway = gateway
        self._offer: SyncManifest | None = None
        self._joined_code = ""
        self._observed_role = "idle"
        self._note = ""
        self._cancel = CancelToken()
        self._poll = QTimer(self)
        self._poll.setInterval(8000)
        self._poll.timeout.connect(self.checkRoomPack)
        self.failed.connect(self._poll.stop)
        self._offerArrived.connect(self._apply_offer)
        self._completed.connect(self._apply_completed)
        self._multiplayer.statusChanged.connect(self._room_changed)

    @Property(bool, constant=True)
    def configured(self) -> bool:
        return self._gateway is not None

    @Property(bool, notify=stateChanged)
    def canShare(self) -> bool:
        status = self._multiplayer.room_snapshot()
        return self._gateway is not None and status.role == "hosting" and bool(status.host_ticket)

    @Property(dict, notify=stateChanged)
    def offer(self) -> dict[str, Any]:
        manifest = self._offer
        if manifest is None:
            return {}
        return {
            "name": manifest.name,
            "gameVersion": manifest.game_version,
            "loader": manifest.loader_kind,
            "loaderVersion": manifest.loader_version,
            "fileCount": len(manifest.files),
            "sizeMiB": round(manifest.total_bytes / 1024**2, 1),
        }

    @Property(str, notify=stateChanged)
    def note(self) -> str:
        return self._note

    @Slot(str)
    def join(self, room_code: str) -> None:
        if self.busy or self._multiplayer.room_snapshot().role != "idle":
            return
        self._joined_code = room_code
        self._multiplayer.join(room_code)

    @Slot(str)
    def publish(self, instance_id: str) -> None:
        if self.busy or not self.canShare:
            self.failed.emit("Cần phòng đang mở và relay hỗ trợ xác thực Plus trước khi chia sẻ.")
            return
        gateway = self._gateway
        if gateway is None:
            return
        status = self._multiplayer.room_snapshot()
        generation = self.next_generation()
        cancel_token = self._cancel = CancelToken()

        def work() -> None:
            self._launcher.publish_room_modpack(
                gateway, status, instance_id, cancel_token=cancel_token
            )
            self._completed.emit(
                "Đã chia sẻ. Bạn bè có mã phòng được đồng bộ miễn phí.", "", generation
            )

        self.run_in_background(work, "Đang chia sẻ ảnh chụp modpack...")

    @Slot()
    def sync(self) -> None:
        if (
            self.busy
            or self._offer is None
            or self._gateway is None
            or self._multiplayer.room_snapshot().role != "joined"
        ):
            return
        gateway, manifest, room_code = self._gateway, self._offer, self._joined_code
        generation = self.next_generation()
        cancel_token = self._cancel = CancelToken()

        def work() -> None:
            instance = self._launcher.sync_room_modpack(
                gateway, room_code, manifest, cancel_token=cancel_token
            )
            self._completed.emit(
                "Đã tạo bản chơi “"
                + instance.label
                + "”. Chọn bản này trong Home để chơi cùng bạn.",
                instance.instance_id,
                generation,
            )

        self.run_in_background(work, "Đang đồng bộ modpack vào bản chơi mới...")

    @Slot()
    def cancel(self) -> None:
        self._cancel.cancel()

    @Slot()
    def _room_changed(self) -> None:
        role = self._multiplayer.room_snapshot().role
        previous, self._observed_role = self._observed_role, role
        if role == "idle":
            self._poll.stop()
            self._cancel.cancel()
            self.next_generation()
            self._offer, self._note = None, ""
        elif (
            role == "joined"
            and previous != "joined"
            and self._gateway is not None
            and self._joined_code
        ):
            self._poll.start()
            self.checkRoomPack()
        self.stateChanged.emit()

    @Slot(object, int)
    def _apply_offer(self, manifest: SyncManifest | None, generation: int) -> None:
        if self.is_current(generation) and self._multiplayer.room_snapshot().role == "joined":
            self._offer = manifest
            if manifest is not None:
                self._poll.stop()
            self.stateChanged.emit()

    @Slot()
    def checkRoomPack(self) -> None:
        if (
            self.busy
            or self._gateway is None
            or not self._joined_code
            or self._multiplayer.room_snapshot().role != "joined"
        ):
            return
        gateway, room_code = self._gateway, self._joined_code
        generation = self.next_generation()

        def work() -> None:
            self._offerArrived.emit(gateway.resolve(room_code), generation)

        self.run_in_background(work, "Đang kiểm tra modpack của phòng...")

    @Slot(str, str, int)
    def _apply_completed(self, note: str, instance_id: str, generation: int) -> None:
        if instance_id:
            self._launcher_bridge.instancesChanged.emit()
        if self.is_current(generation):
            self._note = note
            self.stateChanged.emit()
