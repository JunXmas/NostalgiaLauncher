"""Đồng bộ theo phòng: khách miễn phí, host được backend kiểm Plus ở từng request."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from nostalgia.api import Launcher, RoomSyncGateway, SyncManifest, SyncSnapshot
from nostalgia.errors import MultiplayerError
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.guest_sync_bridge import GuestSyncBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge


class RoomSyncBridge(GuestSyncBridge):
    stateChanged = Signal()
    published = Signal()
    _offerArrived = Signal(object, int)

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
        self._host_ready = True
        self._cancel = CancelToken()
        self._poll = QTimer(self)
        self._poll.setInterval(8000)
        self._poll.timeout.connect(self.checkRoomPack)
        self.failed.connect(self._poll.stop)
        self._offerArrived.connect(self._apply_offer)
        self._completed.connect(self._apply_completed)
        self._multiplayer.statusChanged.connect(self._room_changed)
        self.initialize_guest_review()

    def set_gateway(self, gateway: RoomSyncGateway | None) -> None:
        self._cancel.cancel()
        self.next_generation()
        self._gateway = gateway
        self.clear_guest_review()
        self.stateChanged.emit()

    @Property(bool, notify=stateChanged)
    def configured(self) -> bool:
        return self._gateway is not None

    @Property(bool, notify=stateChanged)
    def canShare(self) -> bool:
        status = self._multiplayer.room_snapshot()
        return self._gateway is not None and status.role == "hosting" and bool(status.host_ticket)

    @Property(bool, notify=stateChanged)
    def hostReady(self) -> bool:
        return self._host_ready

    def set_host_ready(self, ready: bool) -> None:
        self._host_ready = ready
        self.stateChanged.emit()

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
            "basePack": manifest.base_pack.title or manifest.base_pack.project_id
            if manifest.base_pack
            else "",
            "additionalMods": sum(
                sync_file.relative_path.startswith("mods/") and not sync_file.from_base
                for sync_file in manifest.files
            ),
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
        self._publish(instance_id)

    def publish_snapshot(self, snapshot: SyncSnapshot, cancel_token: CancelToken) -> None:
        self._publish(snapshot, cancel_token)

    def _publish(self, source: str | SyncSnapshot, cancel_token: CancelToken | None = None) -> None:
        if self.busy or not self.canShare:
            self.failed.emit("Cần phòng đang mở và relay hỗ trợ xác thực Plus trước khi chia sẻ.")
            return
        gateway = self._gateway
        if gateway is None:
            return
        status = self._multiplayer.room_snapshot()
        generation = self.next_generation()
        cancel_token = self._cancel = cancel_token or CancelToken()

        def work() -> None:
            if isinstance(source, str):
                if getattr(gateway, "requires_live_source", False):
                    raise MultiplayerError(
                        "Hãy mở lại phòng bằng Host & khởi chạy, "
                        "chọn modpack và mod chia sẻ trước khi chơi."
                    )
                self._launcher.publish_room_modpack(
                    gateway, status, source, cancel_token=cancel_token
                )
            else:
                self._launcher.publish_room_snapshot(
                    gateway, status, source, cancel_token=cancel_token
                )
            self._completed.emit(
                "Đã chia sẻ. Bạn bè nhận lời mời được đồng bộ miễn phí.", "", generation
            )

        self.run_in_background(work, "Đang chia sẻ ảnh chụp modpack...")

    @Slot()
    def cancel(self) -> None:
        self._cancel.cancel()
        self.next_generation()

    @Slot()
    def _room_changed(self) -> None:
        role = self._multiplayer.room_snapshot().role
        previous, self._observed_role = self._observed_role, role
        if role == "idle":
            self._poll.stop()
            self._cancel.cancel()
            self.next_generation()
            self._offer, self._note = None, ""
            self.clear_guest_review()
            self._host_ready = True
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
            self._launcher_bridge.announce_instances_changed()
        if self.is_current(generation) and not self._cancel.is_cancelled():
            self._note = note
            self.stateChanged.emit()
            if not instance_id and self._multiplayer.room_snapshot().role == "hosting":
                self.published.emit()
