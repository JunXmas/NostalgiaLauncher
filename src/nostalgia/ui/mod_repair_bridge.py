"""Free quét chỉ đọc; Plus xem phương án, áp dụng có khóa chung và hoàn tác."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Property, Signal, Slot

from nostalgia.api import Launcher, ModScan, RepairGateway, RepairPlan, RepairScan
from nostalgia.errors import NostalgiaError
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.worker import WorkerBridge


class ModRepairBridge(WorkerBridge):
    changed = Signal()
    _arrived = Signal(int, str, object, str)

    def __init__(self, launcher: Launcher, bridge: LauncherBridge) -> None:
        super().__init__(bridge.parent())
        self._launcher, self._bridge = launcher, bridge
        self._gateway: RepairGateway | None = None
        self._scan: ModScan | None = None
        self._plan: RepairPlan | None = None
        self._instance_id = self._receipt_id = self._note = ""
        self._arrived.connect(self._apply)

    @Property(dict, notify=changed)
    def details(self) -> dict[str, Any]:
        return {
            "instanceId": self._instance_id,
            "note": self._note,
            "findings": [
                {"code": finding.code, "file": finding.file_name, "reason": finding.reason}
                for finding in self._scan.findings
            ]
            if self._scan
            else [],
            "scanned": self._scan is not None,
            "fileCount": len(self._scan.archives) if self._scan else 0,
            "changes": [
                {"operation": change.operation, "file": change.file_name, "reason": change.reason}
                for change in self._plan.changes
            ]
            if self._plan
            else [],
            "unresolved": list(self._plan.unresolved) if self._plan else [],
            "canPlan": bool(self._gateway and self._scan and self._scan.findings),
            "canApply": bool(
                self._gateway and self._plan and self._plan.changes and not self._plan.unresolved
            ),
            "canUndo": bool(self._receipt_id),
        }

    def set_gateway(self, gateway: RepairGateway | None) -> None:
        self.next_generation()
        self._gateway, self._plan = gateway, None
        self.changed.emit()

    @Slot(str)
    def scan(self, instance_id: str) -> None:
        if self.busy or self._bridge.busy or self._bridge.storageBusy or self._bridge.gameRunning:
            return
        self._instance_id, self._plan, self._scan = instance_id, None, None
        self._request("scan", lambda: self._launcher.scan_mod_repair(instance_id))

    @Slot()
    def plan(self) -> None:
        gateway, scan = self._gateway, self._scan
        if gateway and scan and not self.busy:
            self._request("plan", lambda: gateway.fetch_plan(scan))

    @Slot()
    def apply(self) -> None:
        gateway, scan, plan = self._gateway, self._scan, self._plan
        if gateway and scan and plan and not self.busy and not self._bridge.gameRunning:
            self._request(
                "applied",
                lambda: self._launcher.apply_mod_repair(
                    self._instance_id, scan, plan, gateway, lambda: bool(self._bridge.gameRunning)
                ),
            )

    @Slot()
    def undo(self) -> None:
        if self._receipt_id and not self.busy and not self._bridge.gameRunning:
            self._request(
                "undone",
                lambda: self._launcher.undo_mod_repair(
                    self._instance_id, self._receipt_id, lambda: bool(self._bridge.gameRunning)
                ),
            )

    def _request(self, operation: str, work: Callable[[], object]) -> None:
        generation = self.next_generation()
        self._bridge.setStorageBusy(True)
        self._note = ""
        self.changed.emit()

        def perform() -> None:
            error, payload = "", None
            try:
                payload = work()
            except NostalgiaError as failure:
                error = str(failure)
            except Exception:
                error = "Tác vụ chưa hoàn tất. Mod và bản sao lưu được giữ để kiểm tra."
            finally:
                self._arrived.emit(generation, operation, payload, error)

        self.run_in_background(perform, "Đang kiểm tra/sửa bộ mod…")

    def _apply(self, generation: int, operation: str, payload: object, error: str) -> None:
        self._bridge.setStorageBusy(False)
        if not self.is_current(generation):
            return
        self._note = error
        if not error:
            if isinstance(payload, RepairScan):
                self._scan = payload.scan
                self._receipt_id = payload.receipt_id
                self._note = (
                    "Đã quét. Không có lỗi metadata được nhận diện."
                    if not payload.scan.findings
                    else "Phát hiện " + str(len(payload.scan.findings)) + " lỗi/điểm chưa xác minh."
                )
            elif isinstance(payload, RepairPlan):
                self._plan = payload
                self._note = "Xem thay đổi và lý do trước khi áp dụng."
            elif operation == "applied" and isinstance(payload, str):
                self._receipt_id, self._plan, self._scan = payload, None, None
                self._note = "Đã sửa và kiểm lại. Bản mod trước sửa được giữ để hoàn tác."
                self._bridge.instancesChanged.emit()
            elif operation == "undone":
                self._receipt_id, self._plan, self._scan = "", None, None
                self._note = "Đã khôi phục bộ mod trước sửa."
                self._bridge.instancesChanged.emit()
        self.changed.emit()
