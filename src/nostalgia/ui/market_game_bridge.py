"""Cấp phiên cosmetic tùy chọn sau khi game khởi động, không chặn luồng chơi."""

import time
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from nostalgia.api import CosmeticGameBridge, Launcher
from nostalgia.errors import NostalgiaError
from nostalgia.model.marketplace import GameCosmeticSession, MarketGateway
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.social_bridge import SocialBridge
from nostalgia.ui.worker import WorkerBridge


class MarketGameBridge(WorkerBridge):
    _arrived = Signal(int, object)

    def __init__(
        self,
        launcher: Launcher,
        main: LauncherBridge,
        social: SocialBridge,
        gateway: MarketGateway | None,
        api_url: str,
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self._launcher, self._social, self._gateway, self._api_url = (
            launcher,
            social,
            gateway,
            api_url,
        )
        self._game_bridge: CosmeticGameBridge | None = None
        self._expires_at = 0
        self._retry_after = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(30_000)
        self._timer.timeout.connect(self.refresh)
        self._arrived.connect(self._apply)
        self.busyChanged.connect(self.refresh)
        main.gameStarted.connect(self._started)
        main.gameStopped.connect(self.close)
        social.sessionChanged.connect(self.close)

    @Slot(str)
    def _started(self, instance_id: str) -> None:
        self.close()
        if not self._gateway or not self._social.signedIn:
            return
        instance = next(
            (
                value
                for value in self._launcher.list_instances()
                if value.instance_id == instance_id
            ),
            None,
        )
        if not instance or instance.runtime_kind != "java" or not instance.nos_client_enabled:
            return
        game_dir: Path = self._launcher.instance_game_dir(instance)
        try:
            self._game_bridge = CosmeticGameBridge(game_dir, self._api_url)
        except OSError:
            return
        self._timer.start()
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        gateway, game = self._gateway, self._game_bridge
        if (
            self.busy
            or not gateway
            or not game
            or self._expires_at > time.time() + 120
            or self._retry_after > time.time()
        ):
            return
        generation = self.next_generation()

        def work() -> None:
            try:
                if not self._expires_at and not gateway.fetch_catalog().enabled:
                    self._arrived.emit(generation, None)
                    return
                game_session = gateway.create_game_session(game.public_key)
                self._arrived.emit(generation, game_session)
            except (NostalgiaError, OSError, ValueError):
                # Cosmetic không sẵn sàng vẫn chơi được, không hiện popup lỗi nền.
                self._arrived.emit(generation, False)

        self.run_in_background(work, "")

    @Slot(int, object)
    def _apply(self, generation: int, game_session: object) -> None:
        if not self.is_current(generation) or self._game_bridge is None:
            return
        if game_session is None:
            self.close()
        elif isinstance(game_session, GameCosmeticSession):
            try:
                self._game_bridge.update(game_session)
                self._expires_at = game_session.expires_at
                self._retry_after = 0
            except OSError:
                self._retry_after = time.time() + 300
        else:
            self._retry_after = time.time() + 300

    @Slot()
    def invalidate(self) -> None:
        self.next_generation()
        self._retry_after = 0
        self._expires_at = 0
        self.refresh()

    @Slot()
    def close(self) -> None:
        self.next_generation()
        self._timer.stop()
        game, self._game_bridge = self._game_bridge, None
        self._expires_at = 0
        self._retry_after = 0
        if game:
            game.close()
