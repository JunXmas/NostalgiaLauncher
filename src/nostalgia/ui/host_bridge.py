"""Choose once, launch once, publish that frozen pack before allowing invitations."""

from __future__ import annotations

from PySide6.QtCore import Slot

from nostalgia.api import SyncSnapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.host_setup import HostSetup


class HostBridge(HostSetup):
    def connect_workflow(self) -> None:
        self._prepared.connect(self._apply_prepared)
        self._bridge.gameStarted.connect(self._game_started)
        self._bridge.gameRunningChanged.connect(self._game_changed)
        self._bridge.failed.connect(self._launch_failed)
        self._bridge.game_lan.lanOpened.connect(self._lan_opened)
        self._multiplayer.statusChanged.connect(self._room_changed)
        self._multiplayer.failed.connect(self._room_failed)
        self._sync.published.connect(self._published)
        self._sync.failed.connect(self._share_failed)
        self._social.sessionChanged.connect(self._session_changed)

    @Slot(str, bool, result=bool)
    def start(self, instance_id: str, share: bool) -> bool:
        error = self._selection_error(instance_id, share)
        if error:
            self._note = error
            self.changed.emit()
            return False
        self._instance_id = instance_id
        self._label = next(
            i["label"] for i in self._bridge.property("instances") if i["instanceId"] == instance_id
        )
        self._share, self._room_seen, self._snapshot = share, False, None
        cancel_token = self._cancel = CancelToken()
        self._sync.set_host_ready(False)
        self._stage_note("preparing", "Đang chuẩn bị bản chơi và bộ modpack đã chọn…")
        self._bridge.play_hosted(
            instance_id, lambda: self._launch_scope(instance_id, share, cancel_token), cancel_token
        )
        return True

    @Slot(object, object)
    def _apply_prepared(self, snapshot: object, cancel_token: object) -> None:
        if cancel_token is self._cancel and not self._cancel.is_cancelled() and self._instance_id:
            self._snapshot = snapshot if isinstance(snapshot, SyncSnapshot) else None
            self._stage_note("launching", "Đang khởi chạy đúng bản chơi đã chọn…")

    @Slot(str)
    def _game_started(self, instance_id: str) -> None:
        if not self._instance_id or instance_id != self._instance_id:
            return
        if self._cancel.is_cancelled() or not self._bridge.gameRunning:
            self.stop()
            return
        self._stage_note("waiting_world", "Vào thế giới → Esc → Open to LAN → Start LAN World.")
        self._multiplayer.start_managed_hosting()

    @Slot(str, int)
    def _lan_opened(self, instance_id: str, port: int) -> None:
        if (
            instance_id == self._instance_id
            and self._stage == "waiting_world"
            and self._multiplayer.room_snapshot().role == "waiting_world"
            and not self._cancel.is_cancelled()
        ):
            self._multiplayer.supplyLanPort(str(port))

    @Slot()
    def _room_changed(self) -> None:
        if not self._instance_id:
            return
        role = self._multiplayer.room_snapshot().role
        if role == "idle":
            if self._room_seen:
                self.stop()
            return
        self._room_seen = True
        self._sync.set_host_ready(self._stage == "ready")
        if role == "waiting_world":
            feed = self._bridge.game_lan
            self._lan_opened(feed.instance_id, feed.port)
        elif role == "hosting" and self._stage == "waiting_world":
            if self._share:
                self.retryShare()
            else:
                self._ready()

    @Slot()
    def retryShare(self) -> None:
        if (
            not self._instance_id
            or not self._share
            or self._snapshot is None
            or self._sync.busy
            or self._cancel.is_cancelled()
            or self._multiplayer.room_snapshot().role != "hosting"
            or not self._bridge.gameRunning
            or self._stage not in ("waiting_world", "error")
        ):
            return
        self._sync.set_host_ready(False)
        self._stage_note(
            "publishing", "Đang đồng bộ modpack của game vừa chạy. Chờ xong để mời bạn."
        )
        self._multiplayer.setLocked(True)
        self._sync.publish_snapshot(self._snapshot, self._cancel)

    @Slot()
    def _published(self) -> None:
        if (
            self._instance_id
            and self._stage == "publishing"
            and not self._cancel.is_cancelled()
            and self._bridge.gameRunning
            and self._multiplayer.room_snapshot().role == "hosting"
        ):
            self._multiplayer.setLocked(False)
            self._ready()

    def _ready(self) -> None:
        self._stage_note(
            "ready",
            "Modpack đã sẵn sàng. Bạn bè nhận lời mời được đồng bộ miễn phí."
            if self._share
            else "Phòng đã sẵn sàng. Bạn bè cần dùng cùng modpack với bạn.",
        )
        self._sync.set_host_ready(True)

    @Slot(str)
    def _share_failed(self, message: str) -> None:
        if self._instance_id and self._stage == "publishing":
            self._stage_note("error", "Chưa đồng bộ được; lời mời vẫn khóa. " + message)

    @Slot(str)
    def _launch_failed(self, message: str) -> None:
        if self._instance_id and self._stage in ("preparing", "launching"):
            self.stop()
            self._stage_note("idle", message)

    @Slot(str)
    def _room_failed(self, message: str) -> None:
        if self._instance_id:
            self._note = message
            self.changed.emit()

    @Slot()
    def _game_changed(self) -> None:
        if self._instance_id and not self._bridge.gameRunning and self._stage != "preparing":
            self.stop()

    @Slot()
    def _session_changed(self) -> None:
        if not self._social.signedIn:
            self.stop()

    @Slot()
    def stop(self) -> None:
        if not self._instance_id:
            return
        self._cancel.cancel()
        self._sync.cancel()
        self._sync.set_host_ready(False)
        self._instance_id, self._snapshot = "", None
        self._stage_note("idle", "Đã dừng phòng. Game đang mở vẫn có thể chơi trên máy bạn.")
        self._multiplayer.stop()
