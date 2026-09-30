"""Cầu nối trang CÀI ĐẶT: thông tin chung của launcher (phiên bản, thư mục dữ liệu), công tắc
âm thanh thông báo và Discord Rich Presence.

Cấu hình đọc từ đĩa MỘT lần rồi giữ trong RAM; chỉ đọc lại sau khi chính cầu nối này ghi.
Trước đây mỗi binding QML và mỗi sự kiện game đều đọc + parse settings.json.

Khoá API CurseForge KHÔNG còn nhập ở đây: thư viện đi qua máy chủ của dự án, ai muốn dùng
khoá riêng thì đặt biến môi trường (xem `settings/store.py`).
"""

from __future__ import annotations

import base64
from dataclasses import replace

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia import __version__
from nostalgia.api import Launcher, Settings
from nostalgia.errors import NostalgiaError

# Mỗi ô mã QR vẽ bằng 4 pixel. Lưới cỡ 6 là 41 ô + viền 4 ô mỗi bên = (41+8)*4 = 196 px,
# và QML vẽ đúng 196 px — không co giãn thì không ô nào rơi vào ranh giới pixel lẻ.
QR_SCALE = 4


class SettingsBridge(QObject):
    notificationSoundChanged = Signal()
    uiSoundChanged = Signal()
    discordChanged = Signal()
    autoUpdateCheckChanged = Signal()
    gameDirRootChanged = Signal()
    gameDirRootError = Signal(str)  # phát khi đường dẫn không hợp lệ — QML hiện thông báo
    hideWhenGameRunningChanged = Signal()

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._settings: Settings | None = None

    def settings_snapshot(self) -> Settings:
        if self._settings is None:
            self._settings = self._launcher.load_settings()
        return self._settings

    def _save(self, wanted: Settings) -> None:
        self._launcher.save_settings(wanted)
        self._settings = wanted

    @Property(bool, notify=notificationSoundChanged)
    def notificationSound(self) -> bool:
        return self.settings_snapshot().notification_sound

    @Property(bool, notify=uiSoundChanged)
    def uiSound(self) -> bool:
        return self.settings_snapshot().ui_sound

    @Property(bool, notify=discordChanged)
    def discordPresence(self) -> bool:
        return self.settings_snapshot().discord_presence

    @Slot(bool)
    def setDiscord(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.discord_presence != enabled:
            self._save(replace(settings, discord_presence=enabled))
            self.discordChanged.emit()

    @Property(str, notify=gameDirRootChanged)
    def defaultGameDirRoot(self) -> str:
        return self.settings_snapshot().default_game_dir_root

    @Slot(str)
    def setDefaultGameDirRoot(self, text: str) -> None:
        """Nhận đường dẫn hoặc URL file:// từ FolderDialog; rỗng = về mặc định."""
        chosen = QUrl(text).toLocalFile() if text.startswith("file:") else text
        try:
            chosen = self._launcher.check_game_dir(chosen)
        except NostalgiaError as exc:
            # Đường dẫn không hợp lệ (ổ gốc, đè lên kho launcher...): báo lỗi rõ ràng.
            # Nếu để exception truyền ra PySide6 sẽ nuốt im lặng và cài đặt không đổi —
            # người dùng vẫn thấy ổ C mặc định mà không biết lý do.
            self.gameDirRootError.emit(str(exc))
            return
        settings = self.settings_snapshot()
        if settings.default_game_dir_root != chosen:
            self._save(replace(settings, default_game_dir_root=chosen))
            self.gameDirRootChanged.emit()

    @Property(bool, notify=autoUpdateCheckChanged)
    def autoUpdateCheck(self) -> bool:
        return self.settings_snapshot().auto_update_check

    @Slot(bool)
    def setAutoUpdateCheck(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.auto_update_check != enabled:
            self._save(replace(settings, auto_update_check=enabled))
            self.autoUpdateCheckChanged.emit()

    @Property(bool, notify=hideWhenGameRunningChanged)
    def hideWhenGameRunning(self) -> bool:
        return self.settings_snapshot().hide_when_game_running

    @Slot(bool)
    def setHideWhenGameRunning(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.hide_when_game_running != enabled:
            self._save(replace(settings, hide_when_game_running=enabled))
            self.hideWhenGameRunningChanged.emit()

    @Slot(bool)
    def setNotificationSound(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.notification_sound != enabled:
            self._save(replace(settings, notification_sound=enabled))
            self.notificationSoundChanged.emit()

    @Slot(bool)
    def setUiSound(self, enabled: bool) -> None:
        settings = self.settings_snapshot()
        if settings.ui_sound != enabled:
            self._save(replace(settings, ui_sound=enabled))
            self.uiSoundChanged.emit()

    @Property(str, constant=True)
    def launcherVersion(self) -> str:
        return __version__

    @Property(str, constant=True)
    def dataDir(self) -> str:
        return str(self._launcher.paths.data_dir)

    @Property(str, constant=True)
    def donateUrl(self) -> str:
        return self._launcher.donate_url()

    @Slot()
    def openDonatePage(self) -> None:
        """Mở trang ủng hộ trong trình duyệt. Chỉ chạy khi người dùng tự bấm."""
        QDesktopServices.openUrl(QUrl(self._launcher.donate_url()))

    @Property(str, constant=True)
    def donateQr(self) -> str:
        """Mã VietQR dạng `data:` URI để QML gán thẳng vào `Image.source`; rỗng khi chưa khai
        số tài khoản.

        Nhúng base64 chứ không ghi file tạm: ảnh chỉ vài KB, và không có file thì không có
        chuyện số tài khoản nằm lại trên đĩa sau khi đóng launcher. `constant=True` được vì
        số ghim trong kho không đổi giữa chừng — bản từ Worker đi đường `donateAccountHolder`
        riêng và chỉ dùng để đối chiếu bằng mắt.
        """
        # scale=4 để ảnh ra đúng (41+8)*4 = 196 px, bằng CHÍNH kích thước QML vẽ nó. Cho Qt
        # co giãn thì ô vuông rơi vào ranh giới pixel lẻ và mã nhoè — đã chụp ra thấy tận mắt.
        png = self._launcher.donate_qr(scale=QR_SCALE)
        if png is None:
            return ""
        return "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    @Property(str, constant=True)
    def donateMemo(self) -> str:
        """Nội dung chuyển khoản mà mã QR điền sẵn — hiện ra để người dùng đối chiếu với app
        ngân hàng trước khi bấm gửi."""
        return self._launcher.donate_memo()

    @Property(str, constant=True)
    def donateAccountHolder(self) -> str:
        """Tên chủ tài khoản, để người quét đối chiếu trước khi gửi tiền. Rỗng khi chưa khai."""
        account = self._launcher.donate_account()
        return "" if account is None else account.holder

    @Property(str, constant=True)
    def communityUrl(self) -> str:
        return self._launcher.community_url()

    @Slot()
    def openCommunityPage(self) -> None:
        """Mở Discord cộng đồng trong trình duyệt. Chỉ chạy khi người dùng tự bấm."""
        QDesktopServices.openUrl(QUrl(self._launcher.community_url()))

    @Slot()
    def openDataFolder(self) -> None:
        """Mở thư mục dữ liệu (versions/libraries/assets/instances) bằng trình quản lý file."""
        folder = self._launcher.paths.data_dir
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
