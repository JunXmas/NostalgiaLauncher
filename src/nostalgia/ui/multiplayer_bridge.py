"""Cầu nối trang CHƠI CHUNG: host mở phòng, bạn nhập mã để vào. Trạng thái tới từ luồng của
dịch vụ phòng; nhảy về luồng giao diện qua tín hiệu xếp hàng của Qt rồi mới đổi thuộc tính.
"""

from __future__ import annotations

from typing import cast

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

from nostalgia.api import Launcher, RoomService, RoomStatus


class MultiplayerBridge(QObject):
    statusChanged = Signal()
    failed = Signal(str)
    _statusArrived = Signal(object)
    _failureArrived = Signal(str)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._status = RoomStatus()
        self._statusArrived.connect(self._apply_status)
        self._failureArrived.connect(self.failed)
        self._service: RoomService = launcher.make_room_service(
            on_status=self._statusArrived.emit, on_failure=self._failureArrived.emit
        )

    # ----- trạng thái -----

    @Property(str, notify=statusChanged)
    def role(self) -> str:
        return self._status.role

    @Property(str, notify=statusChanged)
    def roomCode(self) -> str:
        return self._status.room_code

    @Property(str, notify=statusChanged)
    def roomCodeSpaced(self) -> str:
        """Mã 18 ký tự tách nhóm 6 để đọc qua điện thoại."""
        room_code = self._status.room_code
        return " ".join(room_code[i : i + 6] for i in range(0, len(room_code), 6))

    @Property(int, notify=statusChanged)
    def localPort(self) -> int:
        return self._status.local_port

    @Property(int, notify=statusChanged)
    def joinerCount(self) -> int:
        return self._status.joiner_count

    @Property(bool, notify=statusChanged)
    def locked(self) -> bool:
        return self._status.locked

    @Property(str, notify=statusChanged)
    def worldName(self) -> str:
        return self._status.world_name

    @Property(bool, notify=statusChanged)
    def active(self) -> bool:
        return self._status.role != "idle"

    # ----- lệnh -----

    @Slot()
    def startHosting(self) -> None:
        self._service.start_hosting()

    @Slot(str)
    def join(self, room_code: str) -> None:
        self._service.join(room_code)

    @Slot(bool)
    def setLocked(self, locked: bool) -> None:
        self._service.set_locked(locked)

    @Slot()
    def stop(self) -> None:
        self._service.stop()

    @Slot()
    def copyRoomCode(self) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None and self._status.room_code:
            clipboard.setText(self._status.room_code)

    def shutdown(self) -> None:
        """Gọi khi đóng cửa sổ: dừng phòng và luồng dịch vụ."""
        self._service.shutdown()

    @Slot(object)
    def _apply_status(self, status: object) -> None:
        self._status = cast(RoomStatus, status)
        self.statusChanged.emit()
