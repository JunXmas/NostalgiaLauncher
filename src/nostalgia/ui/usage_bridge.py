"""Điều khiển thống kê tùy chọn; lỗi được cô lập khỏi luồng chơi và thông báo lỗi."""

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from nostalgia.api import Launcher
from nostalgia.ui.settings_bridge import SettingsBridge
from nostalgia.ui.worker import WorkerBridge


class UsageBridge(WorkerBridge):
    changed = Signal()
    payloadRequested = Signal()

    def __init__(
        self, launcher: Launcher, settings: SettingsBridge, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._collector = launcher.usage_collector()
        self._sample = launcher.usage_payload_sample()
        self._timer = QTimer(self)
        self._timer.setInterval(60000)
        self._timer.timeout.connect(self._tick)
        settings.usageChoiceChanged.connect(self._refresh)
        self._refresh()

    @Property(bool, constant=True)
    def available(self) -> bool:
        return self._collector.configuration.ready

    @Property(str, constant=True)
    def endpoint(self) -> str:
        return self._collector.configuration.endpoint

    @Property(str, constant=True)
    def payloadExample(self) -> str:
        return self._sample

    @Property(str, notify=changed)
    def choice(self) -> str:
        return self._settings.settings_snapshot().usage_choice_v1

    @Slot(bool)
    def choose(self, enabled: bool) -> None:
        if enabled and not self._collector.configuration.ready:
            return
        if not enabled:
            self._timer.stop()
            self._collector.revoke()
        self._settings.setUsageChoice("accepted" if enabled else "declined")

    @Slot()
    def showPayload(self) -> None:
        self.payloadRequested.emit()

    @Slot()
    def _refresh(self) -> None:
        if (
            self._settings.settings_snapshot().usage_choice_v1 == "accepted"
            and self._collector.configuration.ready
        ):
            self._collector.resume()
            self._timer.start()
            self._tick()
        else:
            self._timer.stop()
            self._collector.revoke()
        self.changed.emit()

    @Slot()
    def _tick(self) -> None:
        if self.busy:
            return
        attempt = self._collector.new_attempt()
        if attempt is not None:
            self.run_in_background(lambda: self._collector.send_active(attempt), "")

    @Slot()
    def shutdown(self) -> None:
        self._timer.stop()
        self._collector.shutdown()
