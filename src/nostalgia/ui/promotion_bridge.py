"""Slide quảng cáo trang chủ cho QML: tải feed ở luồng nền lúc mở, mở link bằng trình duyệt."""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from nostalgia.api import Launcher, Promotion
from nostalgia.ui.worker import WorkerBridge


class PromotionBridge(WorkerBridge):
    changed = Signal()
    _loaded = Signal(object)

    def __init__(self, launcher: Launcher, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._launcher = launcher
        self._promotions: tuple[Promotion, ...] = ()
        self._loaded.connect(self._apply)
        # Để cửa sổ vẽ xong trước; feed chậm không làm trang chủ chờ.
        QTimer.singleShot(0, lambda: self.run_in_background(self._load, "Tải tin trang chủ"))

    def _load(self) -> None:
        self._loaded.emit(self._launcher.load_promotions())

    @Slot(object)
    def _apply(self, promotions: tuple[Promotion, ...]) -> None:
        self._promotions = promotions
        self.changed.emit()

    @Property(list, notify=changed)
    def slides(self) -> list[dict[str, Any]]:
        now = time.time()
        return [
            {
                "kind": promotion.slide_type,
                "title": promotion.title,
                "body": promotion.body,
                "button": promotion.button,
                "target": promotion.target,
                "image": QUrl.fromLocalFile(str(promotion.image)).toString()
                if promotion.image
                else "",
            }
            for promotion in self._promotions
            if promotion.showing(now)
        ]

    @Slot(str)
    def openLink(self, url: str) -> None:
        # Chỉ mở link của slide đang hiện (đã kiểm https), không mở chuỗi tuỳ ý QML đưa vào.
        now = time.time()
        if any(
            p.slide_type == "link" and p.target == url and p.showing(now) for p in self._promotions
        ):
            QDesktopServices.openUrl(QUrl(url))
