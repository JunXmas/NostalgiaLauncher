"""Chọn bản chơi và giữ bộ mod cố định trong suốt phiên chia sẻ của host."""

from __future__ import annotations

import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from nostalgia.api import Launcher, SyncSnapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.host_selection import HostModSelection
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.social_bridge import SocialBridge


class HostSetup(QObject):
    changed = Signal()
    setupRequested = Signal()
    _prepared = Signal(object, object)

    def __init__(
        self,
        launcher: Launcher,
        bridge: LauncherBridge,
        multiplayer: MultiplayerBridge,
        sync_bridge: RoomSyncBridge,
        social: SocialBridge,
        *,
        plus_enabled: bool,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._launcher, self._bridge, self._multiplayer = launcher, bridge, multiplayer
        self._sync, self._social, self._plus_enabled = sync_bridge, social, plus_enabled
        self._instance_id, self._label, self._stage, self._note = "", "", "idle", ""
        self._share = self._room_seen = False
        self._snapshot: SyncSnapshot | None = None
        self._cancel = CancelToken()
        self._mod_selection = HostModSelection(launcher, self)
        self._excluded_mods: frozenset[str] | None = None
        self._deferred_launch = False
        self._launch_event = threading.Event()
        self._game_seen = False
        self._pack_published = False
        social.changed.connect(self.changed)
        sync_bridge.stateChanged.connect(self.changed)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        return {
            "active": bool(self._instance_id),
            "instanceId": self._instance_id,
            "label": self._label,
            "stage": self._stage,
            "share": self._share,
            "note": self._note,
            "deferred": self._deferred_launch,
        }

    @Property(QObject, constant=True)
    def modSelection(self) -> QObject:
        return self._mod_selection

    @Property(bool, notify=changed)
    def syncAvailable(self) -> bool:
        return bool(
            self._plus_enabled
            and self._social.signedIn
            and self._social.property("account").get("plus")
            and self._sync.configured
        )

    @Slot()
    def openSetup(self) -> None:
        if not self._instance_id and not self._multiplayer.active:
            self.setupRequested.emit()

    def _stage_note(self, stage: str, note: str) -> None:
        self._stage, self._note = stage, note
        self.changed.emit()

    def _selection_error(self, instance_id: str, share: bool) -> str:
        if self._instance_id or self._multiplayer.active:
            return "Hãy rời phòng hiện tại trước khi mở phòng mới."
        if self._bridge.busy or self._bridge.gameRunning or self._bridge.storageBusy:
            return "Hãy đóng game và đợi thao tác hiện tại xong trước khi host bản chơi đã chọn."
        if not self._social.signedIn:
            return "Đăng nhập Google để mở phòng và mời bạn bè."
        if not self._bridge.activeAccountId:
            return "Thêm tài khoản Minecraft trước khi khởi chạy game."
        if not any(i["instanceId"] == instance_id for i in self._bridge.property("instances")):
            return "Bản chơi đã chọn không còn tồn tại."
        if share and not self.syncAvailable:
            return "Đồng bộ cần Plus đang hoạt động và dịch vụ hỗ trợ; hiện chưa khả dụng."
        if share and self._mod_selection.pending_for(instance_id):
            return "Hãy đợi danh sách mod tải xong; nếu có lỗi, chọn lại bản chơi."
        if self._sync.busy:
            return "Hãy đợi thao tác đồng bộ trước đó dừng hoàn toàn."
        return ""

    @contextmanager
    def _launch_scope(
        self, instance_id: str, share: bool, cancel_token: CancelToken
    ) -> Iterator[None]:
        cancel_token.raise_if_cancelled()
        try:
            if share:
                self._launcher.paths.data_dir.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(
                    prefix="room-host-", dir=self._launcher.paths.data_dir
                ) as temporary:
                    excluded = self._excluded_mods
                    if excluded is None:
                        excluded = self._launcher.load_room_share_options(instance_id)
                    self._launcher.save_room_share_options(instance_id, excluded)
                    snapshot = self._launcher.capture_room_modpack(
                        instance_id,
                        Path(temporary),
                        cancel_token=cancel_token,
                        excluded_mods=excluded,
                    )
                    cancel_token.raise_if_cancelled()
                    self._prepared.emit(snapshot, cancel_token)
                    try:
                        self._wait_for_launch(cancel_token)
                        if self._deferred_launch:
                            self._launcher.verify_room_snapshot(
                                instance_id, snapshot, excluded, cancel_token
                            )
                        yield
                    finally:
                        cancel_token.cancel()
            else:
                self._prepared.emit(None, cancel_token)
                self._wait_for_launch(cancel_token)
                yield
        finally:
            cancel_token.cancel()

    def _wait_for_launch(self, cancel_token: CancelToken) -> None:
        if self._deferred_launch:
            while not self._launch_event.wait(0.1):
                cancel_token.raise_if_cancelled()
        cancel_token.raise_if_cancelled()
