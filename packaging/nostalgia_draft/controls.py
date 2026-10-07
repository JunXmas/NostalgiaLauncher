"""Explicit local QA actions; no service account credentials or remote entitlement writes."""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.payment_bridge import PaymentBridge
from nostalgia.ui.server_controller import ServerController
from nostalgia.ui.social_bridge import SocialBridge
from nostalgia.ui.worker import WorkerBridge
from nostalgia_draft.payment import ReviewPayment
from nostalgia_draft.server import ReviewServer
from nostalgia_draft.social import ReviewSocial
from nostalgia_draft.sync import ReviewSync


class ReviewControls(WorkerBridge):
    changed = Signal()
    completed = Signal(str)

    def __init__(self, launcher: Launcher, social: ReviewSocial, payment: ReviewPayment) -> None:
        super().__init__()
        self._launcher, self._social, self._payment = launcher, social, payment
        self._bridge: LauncherBridge | None = None
        self._social_bridge: SocialBridge | None = None
        self._servers: ServerController | None = None
        self._payments: PaymentBridge | None = None
        self._note = (
            "Ultimate TEST · Quyền đầy đủ. Chat/thanh toán mô phỏng; Google cần backend thật."
        )
        self._syncing = False
        self._cancel = CancelToken()
        self.completed.connect(self._finish)
        self.failed.connect(self._finish)

    def attach(
        self,
        bridge: LauncherBridge,
        social: SocialBridge,
        servers: ServerController,
        payments: PaymentBridge,
    ) -> None:
        self._bridge, self._social_bridge = bridge, social
        self._servers, self._payments = servers, payments

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    @Slot(str)
    def selectPlan(self, plan_id: str) -> None:
        if self.busy or (self._servers and self._servers.busy):
            return
        if self._servers and self._servers.domain_manager.running_id:
            self._set_note("Dừng server trước khi đổi gói TEST.")
            return
        self._social.access_token = "draft-local-session-not-a-service-credential"
        self._social.select_plan(plan_id)
        if self._social_bridge:
            self._social_bridge.refresh()
        if self._servers:
            self._servers.set_gateway(ReviewServer(self._social))
            self._servers.checkAccess()
        self._set_note("Đã chọn gói TEST. Không thay đổi quyền trên tài khoản Google thật.")

    @Slot()
    def simulatePaid(self) -> None:
        self._payment.paid = True
        if self._payments:
            self._payments.checkPayment()
        self._set_note("Thanh toán thành công MÔ PHỎNG; không có giao dịch ngân hàng.")

    @Slot(str)
    def syncLocal(self, instance_id: str) -> None:
        bridge = self._bridge
        if not bridge or self.busy or bridge.busy or bridge.storageBusy or bridge.gameRunning:
            self._set_note("Dừng game và đợi thao tác hiện tại trước khi thử đồng bộ.")
            return
        self._cancel = CancelToken()
        self._syncing = True
        bridge.setStorageBusy(True)

        def work() -> None:
            with tempfile.TemporaryDirectory(prefix="nostalgia-draft-sync-") as directory:
                gateway = ReviewSync(Path(directory))
                status = RoomStatus(
                    role="hosting", room_code="DRAFT-LOCAL", host_ticket="local-test"
                )
                self._launcher.publish_room_modpack(
                    gateway, status, instance_id, cancel_token=self._cancel
                )
                manifest = gateway.resolve(status.room_code)
                assert manifest is not None
                instance = self._launcher.sync_room_modpack(
                    gateway, status.room_code, manifest, cancel_token=self._cancel
                )
            self.completed.emit("Đã tạo bản chơi đồng bộ local: " + instance.display_name)

        self.run_in_background(work, "Đang kiểm hash và tạo bản chơi đồng bộ local…")

    @Slot(str)
    def _finish(self, message: str) -> None:
        if self._bridge and self._syncing:
            self._syncing = False
            self._bridge.setStorageBusy(False)
            self._bridge.instancesChanged.emit()
        self._set_note(message)

    def _set_note(self, message: str) -> None:
        self._note = message
        self.changed.emit()

    @Slot()
    def cancel(self) -> None:
        self._cancel.cancel()
