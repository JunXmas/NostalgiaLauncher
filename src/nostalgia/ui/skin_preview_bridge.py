"""Một worker cho skin 3D; QML chỉ dịch atlas đã nạp, không gọi Python trên render thread."""

from __future__ import annotations

import logging
import threading
from collections import OrderedDict, deque
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from nostalgia.ui.skin_frame_cache import SkinFrameCache
from nostalgia.ui.skin_sprite import SkinPreview, ensure_skin_preview, prune_skin_previews
from nostalgia.ui.worker import WorkerBridge

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SkinRequest:
    source: str
    slim: bool
    revision: str
    animated: bool
    cape_source: str = ""
    preview_frame: int = 5

    @property
    def key(self) -> str:
        return (
            self.source
            + ("|1|" if self.slim else "|0|")
            + self.revision
            + "|cape|"
            + self.cape_source
            + "|view|"
            + str(self.preview_frame)
        )


class SkinPreviewBridge(WorkerBridge):
    previewsChanged = Signal()

    def __init__(self, data_dir: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cache_dir = data_dir / "cache" / "skin-preview"
        self._renderer = SkinFrameCache()
        self._previews: OrderedDict[str, str] = OrderedDict()
        self._atlases: OrderedDict[str, str] = OrderedDict()
        self._pending: deque[SkinRequest] = deque()
        self._queued: set[SkinRequest] = set()
        self._queue_lock = threading.Lock()
        self._draining = False

    @Property("QVariant", notify=previewsChanged)  # type: ignore[arg-type]
    def previews(self) -> dict[str, str]:
        with self._queue_lock:
            return dict(self._previews)

    @Property("QVariant", notify=previewsChanged)  # type: ignore[arg-type]
    def atlases(self) -> dict[str, str]:
        with self._queue_lock:
            return dict(self._atlases)

    @Slot(str, bool, str, bool)
    @Slot(str, bool, str, bool, str)
    @Slot(str, bool, str, bool, str, int)
    def ensurePreview(
        self,
        source: str,
        slim: bool,
        revision: str,
        animated: bool,
        cape_source: str = "",
        preview_frame: int = 5,
    ) -> None:
        request = SkinRequest(source, slim, revision, animated, cape_source, preview_frame)
        with self._queue_lock:
            if request.key in self._previews and (not animated or request.key in self._atlases):
                return
            if request in self._queued:
                return
            self._queued.add(request)
            if animated:
                self._pending.appendleft(request)
            else:
                self._pending.append(request)
            start_worker = not self._draining
            self._draining = True
        if start_worker:
            self.run_in_background(self._drain)

    def _drain(self) -> None:
        while True:
            with self._queue_lock:
                if not self._pending:
                    self._draining = False
                    return
                request = self._pending.popleft()
            try:
                preview = ensure_skin_preview(
                    self._cache_dir,
                    self._renderer,
                    request.source,
                    request.slim,
                    request.revision,
                    False,
                    request.cape_source,
                    request.preview_frame,
                )
                self._publish(request, preview)
                if request.animated:
                    preview = ensure_skin_preview(
                        self._cache_dir,
                        self._renderer,
                        request.source,
                        request.slim,
                        request.revision,
                        True,
                        request.cape_source,
                        request.preview_frame,
                    )
                    self._publish(request, preview)
            except OSError:
                logger.warning("không ghi được cache skin 3D", exc_info=True)
            finally:
                with self._queue_lock:
                    self._queued.discard(request)

    def _publish(self, request: SkinRequest, preview: SkinPreview) -> None:
        with self._queue_lock:
            self._previews[request.key] = QUrl.fromLocalFile(str(preview.thumbnail)).toString()
            self._previews.move_to_end(request.key)
            if preview.atlas:
                self._atlases[request.key] = QUrl.fromLocalFile(str(preview.atlas)).toString()
                self._atlases.move_to_end(request.key)
            if len(self._previews) > 48:
                self._previews.popitem(last=False)
            if len(self._atlases) > 8:
                self._atlases.popitem(last=False)
            protected = frozenset(
                Path(QUrl(url).toLocalFile())
                for url in (*self._previews.values(), *self._atlases.values())
            )
        self.previewsChanged.emit()
        prune_skin_previews(self._cache_dir, protected)
