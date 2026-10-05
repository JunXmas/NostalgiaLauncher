"""Cầu nối tự cập nhật: kiểm bản mới (tự động lúc khởi động nếu bật, hoặc bấm nút), tải +
kiểm băm ở luồng nền có tiến độ, rồi áp và mở lại (gói đóng sẵn) hoặc mở trang tải (mã nguồn).

Trạng thái là MỘT máy trạng thái nhỏ: idle → checking → upToDate | available → downloading →
ready → applying; lỗi ở đâu về `failed` kèm câu lỗi. QML chỉ vẽ theo `state`.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import (
    SELF_UPDATING_KINDS,
    Launcher,
    LauncherRelease,
    Progress,
    StagedUpdate,
)
from nostalgia.ui.worker import WorkerBridge

STARTUP_CHECK_DELAY_MS = 3000


class UpdateBridge(WorkerBridge):
    stateChanged = Signal()
    progressChanged = Signal()
    updateAvailable = Signal(str)
    _outcome = Signal(str, str)  # state, message — từ luồng nền về luồng giao diện

    def __init__(
        self,
        launcher: Launcher,
        *,
        check_enabled: Callable[[], bool],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._check_enabled = check_enabled
        self._state = "idle"
        self._message = ""
        self._progress_fraction = 0.0
        self._release: LauncherRelease | None = None
        self._staged: StagedUpdate | None = None
        # Bấm "Cập nhật ngay" là một nhịp: tải xong thì áp luôn, không bắt bấm nút thứ hai.
        self._apply_when_ready = False
        self._outcome.connect(self._apply_outcome)
        # Kiểm lúc khởi động nhưng để cửa sổ vẽ xong trước — người dùng không chờ GitHub để thấy UI.
        QTimer.singleShot(STARTUP_CHECK_DELAY_MS, self._check_on_startup)

    # ----- trạng thái cho QML -----

    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(str, notify=stateChanged)
    def message(self) -> str:
        return self._message

    @Property(str, notify=stateChanged)
    def latestVersion(self) -> str:
        return self._release.launcher_version if self._release else ""

    @Property(str, notify=stateChanged)
    def releaseNotes(self) -> str:
        return self._release.notes if self._release else ""

    @Property(str, constant=True)
    def installKind(self) -> str:
        return self._launcher.launcher_install_kind()

    @Property(bool, constant=True)
    def canSelfUpdate(self) -> bool:
        """Kiểu cài này tự lên bản mới được (tráo thư mục / thay .AppImage / cài đè .deb)?

        QML hỏi cái này chứ đừng so `installKind === "frozen"`: thêm một kiểu tự cập nhật
        được mà quên sửa QML thì nút lặng lẽ biến thành "Mở trang tải", không gì đỏ."""
        return self._launcher.launcher_install_kind() in SELF_UPDATING_KINDS

    @Property(float, notify=progressChanged)
    def progressFraction(self) -> float:
        return self._progress_fraction

    def report_progress(self, progress: Progress) -> None:
        """Từ luồng tải; tín hiệu xếp hàng về luồng giao diện."""
        self._progress_fraction = progress.fraction
        self.progressChanged.emit()

    # ----- lệnh -----

    @Slot()
    def checkNow(self) -> None:
        if self.busy or self._state in ("checking", "downloading", "applying"):
            return
        self._set_state("checking", "Đang hỏi GitHub...")

        def work() -> None:
            # Bắt MỌI ngoại lệ: lỗi lạ nào cũng phải về `failed`, không được để trạng thái kẹt
            # ở "checking" mãi (nút bị khoá, người dùng không làm gì được).
            try:
                release = self._launcher.check_launcher_update()
            except Exception as exc:
                self._outcome.emit("failed", f"Không kiểm được: {exc}")
                return
            self._release = release
            if release is None:
                self._outcome.emit("upToDate", "Bạn đang dùng bản mới nhất")
            else:
                self._outcome.emit("available", f"Có bản {release.launcher_version}")

        self.run_in_background(work, "Kiểm tra bản mới")

    @Slot()
    def download(self) -> None:
        release = self._release
        if release is None or self._state == "downloading":
            return
        self._set_state("downloading", f"Đang tải bản {release.launcher_version}...")

        def work() -> None:
            try:
                self._staged = self._launcher.download_launcher_update(
                    release, on_progress=self.report_progress
                )
            except Exception as exc:
                self._outcome.emit("failed", f"Không tải được: {exc}")
                return
            self._outcome.emit("ready", f"Bản {release.launcher_version} đã sẵn sàng")

        self.run_in_background(work, f"Tải bản {release.launcher_version}")

    @Slot()
    def updateNow(self) -> None:
        """MỘT nút cho cả việc: tải xong thì tự áp và mở lại, người dùng không bấm gì thêm.

        Gói `.zip` tráo thư mục, AppImage thay chính file đang chạy, `.deb`/`.rpm` nhờ trình
        quản lý gói cài đè. Kiểu không tự lên được (mã nguồn, macOS .app) thì mở thẳng trang
        tải, thay vì tải cả gói rồi mới báo không cài được.
        """
        if self._launcher.launcher_install_kind() not in SELF_UPDATING_KINDS:
            self.openReleasePage()
            return
        self._apply_when_ready = True
        self.download()

    @Slot()
    def applyAndRestart(self) -> None:
        """Gói đóng sẵn: chạy script tráo rồi thoát launcher. Mã nguồn: chỉ mở trang tải."""
        if self._staged is None:
            # Không nên xảy ra — nút chỉ hiện khi state=="ready", nhưng phòng hờ
            self._set_state("failed", "Chưa tải xong bản mới — vui lòng tải lại")
            return
        try:
            self._launcher.apply_launcher_update(self._staged)
        except Exception as exc:
            # Bắt TẤT CẢ exception — kể cả lỗi hệ thống (PermissionError, OSError...)
            # vì nếu chỉ bắt NostalgiaError thì PySide6 nuốt im lặng, người dùng không biết
            self._set_state("failed", f"Không áp được bản mới: {exc}")
            return
        self._set_state("applying", "Đang mở lại launcher...")
        # QUAN TRỌNG: QGuiApplication.quit() là async, nó không thoát ngay.
        # Dùng os._exit() để thoát NGAY LẬP TỨC, không đợi event loop.
        # Nếu không script sẽ đợi hết timeout 60s và thoát mà không làm gì.
        import os

        os._exit(0)

    @Slot()
    def openReleasePage(self) -> None:
        if self._release is not None and self._release.page_url:
            QDesktopServices.openUrl(QUrl(self._release.page_url))

    # ----- nội bộ -----

    def _check_on_startup(self) -> None:
        if self._check_enabled():
            self.checkNow()

    @Slot(str, str)
    def _apply_outcome(self, state: str, message: str) -> None:
        self._set_state(state, message)
        if state == "available" and self._release is not None:
            self.updateAvailable.emit(self._release.launcher_version)
        if state == "ready" and self._apply_when_ready:
            # Nhịp hai của "Cập nhật ngay". Chạy trên luồng giao diện (tín hiệu `_outcome` đã
            # xếp hàng về đây), nên tráo file và thoát app đều an toàn.
            self._apply_when_ready = False
            self.applyAndRestart()
        elif state == "failed":
            self._apply_when_ready = False

    def _set_state(self, state: str, message: str) -> None:
        self._state, self._message = state, message
        self.stateChanged.emit()
