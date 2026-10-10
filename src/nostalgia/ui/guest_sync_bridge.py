"""Khách xem nội dung, chọn file và xác nhận rủi ro trước khi đồng bộ."""

from dataclasses import replace
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from nostalgia.api import Launcher, RoomSyncGateway, SyncManifest
from nostalgia.errors import MultiplayerError
from nostalgia.model.pack import SyncReview
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.worker import WorkerBridge


class GuestSyncBridge(WorkerBridge):
    reviewChanged = Signal()
    reviewRequested = Signal()
    _reviewArrived = Signal(object, object, int)
    _completed = Signal(str, str, int)
    _storageReleased = Signal()
    _launcher: Launcher
    _launcher_bridge: LauncherBridge
    _multiplayer: MultiplayerBridge
    _gateway: RoomSyncGateway | None
    _offer: SyncManifest | None
    _joined_code: str
    _cancel: CancelToken
    _guest_instance_id: str

    @Property(str, notify=reviewChanged)
    def guestInstanceId(self) -> str:
        return self._guest_instance_id

    @Slot(str)
    def launchGuest(self, instance_id: str) -> None:
        status = self._multiplayer.room_snapshot()
        if (
            status.role != "joined"
            or not status.world_ready
            or status.local_port <= 0
            or status.connection_kind == "connecting"
        ):
            return
        if (
            self.busy
            or self._launcher_bridge.busy
            or self._launcher_bridge.gameRunning
            or self._launcher_bridge.storageBusy
        ):
            return
        if status.share_state == "pending" and self._offer is None:
            return
        selected = self._guest_instance_id if self._offer is not None else instance_id
        if not selected or not any(
            instance["instanceId"] == selected
            for instance in self._launcher_bridge.property("instances")
        ):
            return
        self._launcher_bridge.playServer(selected, f"127.0.0.1:{status.local_port}")

    def initialize_guest_review(self) -> None:
        self._review = SyncReview(())
        self._review_manifest: SyncManifest | None = None
        self._reviewArrived.connect(self._apply_review)
        self._storageReleased.connect(lambda: self._launcher_bridge.setStorageBusy(False))

    @Property(list, notify=reviewChanged)
    def guestChoices(self) -> list[dict[str, Any]]:
        return [
            {
                "path": choice.relative_path,
                "title": choice.title,
                "icon": choice.icon_url,
                "kind": choice.content_kind,
                "enabled": choice.enabled,
                "selected": choice.selected,
                "added": choice.added,
            }
            for choice in self._review.choices
        ]

    @Property(str, notify=reviewChanged)
    def updateLabel(self) -> str:
        return self._review.instance_label

    @Property(bool, notify=reviewChanged)
    def reviewReady(self) -> bool:
        return self._review_manifest is not None and self._review_manifest == self._offer

    @Slot(str, bool)
    def setGuestSelected(self, relative_path: str, selected: bool) -> None:
        if self.busy:
            return
        self._review = replace(
            self._review,
            choices=tuple(
                replace(choice, selected=selected)
                if choice.relative_path == relative_path
                else choice
                for choice in self._review.choices
            ),
        )
        self.reviewChanged.emit()

    @Slot(bool, str)
    def selectGuestAll(self, selected: bool, content_kind: str) -> None:
        if self.busy:
            return
        self._review = replace(
            self._review,
            choices=tuple(
                replace(choice, selected=selected)
                if choice.content_kind == content_kind
                else choice
                for choice in self._review.choices
            ),
        )
        self.reviewChanged.emit()

    def clear_guest_review(self) -> None:
        self._review_manifest = None
        self._review = SyncReview(())
        self.reviewChanged.emit()

    def _guest_available(self) -> bool:
        return bool(
            not self.busy
            and self._offer is not None
            and self._gateway is not None
            and self._multiplayer.room_snapshot().role == "joined"
        )

    @Slot()
    def sync(self) -> None:
        if not self._guest_available():
            return
        manifest = self._offer
        assert manifest is not None
        self.clear_guest_review()
        generation = self.next_generation()

        def work() -> None:
            review = self._launcher.review_room_modpack(manifest)
            self._reviewArrived.emit(review, manifest, generation)

        self.run_in_background(work, "Đang đọc nội dung và bản chơi đã đồng bộ…")

    @Slot(object, object, int)
    def _apply_review(self, review: SyncReview, manifest: SyncManifest, generation: int) -> None:
        if (
            self.is_current(generation)
            and manifest == self._offer
            and self._multiplayer.room_snapshot().role == "joined"
        ):
            self._review, self._review_manifest = review, manifest
            self.reviewChanged.emit()
            self.reviewRequested.emit()

    @Slot(bool, result=bool)
    def confirmSync(self, acknowledged: bool) -> bool:
        if not self._guest_available() or not self.reviewReady:
            return False
        if not acknowledged:
            self.failed.emit("Hãy đọc và xác nhận cảnh báo bảo mật trước khi nhận file.")
            return False
        if (
            self._launcher_bridge.busy
            or self._launcher_bridge.storageBusy
            or self._launcher_bridge.gameRunning
        ):
            self.failed.emit("Hãy đóng game và đợi thao tác hiện tại xong trước khi cập nhật.")
            return False
        gateway, manifest, room_code = self._gateway, self._offer, self._joined_code
        assert gateway is not None and manifest is not None
        review = self._review
        excluded = frozenset(
            choice.relative_path.removesuffix(".disabled")
            for choice in review.choices
            if not choice.selected
        )
        generation = self.next_generation()
        cancel_token = self._cancel = CancelToken()
        self._launcher_bridge.setStorageBusy(True)
        initial_attempt = True

        def work() -> None:
            nonlocal initial_attempt
            acquired, initial_attempt = initial_attempt, False
            try:
                cancel_token.raise_if_cancelled()
                if (
                    not self.is_current(generation)
                    or self._multiplayer.room_snapshot().role != "joined"
                    or self._launcher_bridge.busy
                    or self._launcher_bridge.gameRunning
                    or (not acquired and self._launcher_bridge.storageBusy)
                ):
                    raise MultiplayerError("Hãy đóng game và mở lại lựa chọn đồng bộ.")
                self._launcher_bridge.setStorageBusy(True)
                acquired = True
                cancel_token.raise_if_cancelled()
                if self._launcher.review_room_modpack(manifest).instance_id != review.instance_id:
                    raise MultiplayerError("Bản chơi cập nhật đã thay đổi. Hãy mở lại lựa chọn.")
                instance = self._launcher.sync_room_modpack(
                    gateway, room_code, manifest, cancel_token=cancel_token, excluded_paths=excluded
                )
                self._completed.emit(
                    ("Đã cập nhật “" if review.instance_id else "Đã tạo bản chơi “")
                    + instance.label
                    + "”. Chọn bản này ở Trang chủ để chơi cùng bạn.",
                    instance.instance_id,
                    generation,
                )
            finally:
                if acquired:
                    self._storageReleased.emit()

        self.run_in_background(
            work, "Đang cập nhật bản chơi…" if review.instance_id else "Đang nhận modpack…"
        )
        return True
