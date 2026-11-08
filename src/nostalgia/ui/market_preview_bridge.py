"""Một hàng đợi preview giới hạn; bỏ kết quả cũ khi đổi món hoặc skin."""

import hashlib
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from nostalgia.errors import NostalgiaError
from nostalgia.model.cosmetic import CosmeticAsset
from nostalgia.model.marketplace import MarketGateway
from nostalgia.ui.market_render import build_market_faces, render_market
from nostalgia.ui.worker import WorkerBridge


class MarketPreviewBridge(WorkerBridge):
    changed = Signal()
    _arrived = Signal(int, str, str)

    def __init__(self, gateway: MarketGateway | None, cache_dir: Path, parent: QObject) -> None:
        super().__init__(parent)
        self._gateway, self._cache_dir = gateway, cache_dir
        self._source, self._note = "", ""
        self._subject: tuple[str, bool, str] | None = None
        self._models: OrderedDict[str, CosmeticAsset] = OrderedDict()
        self._pending: tuple[int, str, bool, str, float] | None = None
        self._arrived.connect(self._apply)
        self.busyChanged.connect(self._drain)

    @Property(str, notify=changed)
    def source(self) -> str:
        return self._source

    @Property(str, notify=changed)
    def note(self) -> str:
        return self._note

    @Slot(str, bool, str, float)
    def show(self, source: str, slim: bool, digest: str, yaw: float) -> None:
        digests = digest.split(",") if digest else []
        if (
            len(digests) > 6
            or any(len(value) != 64 for value in digests)
            or not -10000 < yaw < 10000
        ):
            return
        generation = self.next_generation()
        subject = (source, slim, digest)
        if self._subject != subject:
            self._subject = subject
            self._source = self._note = ""
            self.changed.emit()
        self._pending = (generation, source, slim, digest, yaw)
        self._drain()

    @Slot()
    def _drain(self) -> None:
        if self.busy or self._pending is None:
            return
        generation, source, slim, digest, yaw = self._pending
        self._pending = None
        gateway = self._gateway

        def work() -> None:
            try:
                cosmetics = []
                for digest_value in digest.split(",") if digest else ():
                    cosmetic = self._models.get(digest_value)
                    if cosmetic is None and gateway:
                        cosmetic = gateway.sync_asset(digest_value, self._cache_dir / "assets")
                        self._models[digest_value] = cosmetic
                        if len(self._models) > 12:
                            self._models.popitem(last=False)
                    if cosmetic:
                        cosmetics.append(cosmetic)
                faces = build_market_faces(source, slim, tuple(cosmetics))
                image = render_market(faces, yaw)
                destination = self._cache_dir / f"preview-{generation % 8}.png"
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not image.save(str(destination)):
                    raise OSError("Unable to save cosmetic preview")
                marker = hashlib.sha256(
                    f"{source}:{slim}:{digest}:{yaw}:{generation}".encode()
                ).hexdigest()[:16]
                self._arrived.emit(
                    generation,
                    QUrl.fromLocalFile(str(destination)).toString() + "?revision=" + marker,
                    "",
                )
            except (NostalgiaError, OSError, ValueError) as error:
                self._arrived.emit(generation, "", str(error))

        self.run_in_background(work, "Đang dựng preview cosmetic…")

    @Slot(int, str, str)
    def _apply(self, generation: int, source: str, error: str) -> None:
        if self.is_current(generation):
            self._source, self._note = source, error
            self.changed.emit()
