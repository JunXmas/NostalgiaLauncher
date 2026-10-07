"""Đo dựng atlas lần đầu, mở cache và bộ nhớ; không coi đây là benchmark GPU người dùng."""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from nostalgia.ui.skin_frame_cache import MAX_FRAME_CACHE, SkinFrameCache
from nostalgia.ui.skin_renderer import FRAME_HEIGHT, FRAME_WIDTH
from nostalgia.ui.skin_sprite import ensure_skin_preview


def main() -> None:
    application = QApplication([])
    source_path = Path(__file__).resolve().parents[1] / "src/nostalgia/skin/defaults/steve.png"
    source = QUrl.fromLocalFile(str(source_path)).toString()
    cold_times: list[float] = []
    warm_times: list[float] = []
    with tempfile.TemporaryDirectory() as temporary:
        for number in range(5):
            cache_dir = Path(temporary) / str(number)
            renderer = SkinFrameCache()
            before = time.perf_counter()
            preview = ensure_skin_preview(cache_dir, renderer, source, False, "", True)
            cold_times.append((time.perf_counter() - before) * 1000)
            before = time.perf_counter()
            ensure_skin_preview(cache_dir, SkinFrameCache(), source, False, "", True)
            warm_times.append((time.perf_counter() - before) * 1000)
        assert preview.atlas is not None
        print(
            json.dumps(
                {
                    "cold_atlas_median_ms": round(statistics.median(cold_times), 3),
                    "disk_cache_median_ms": round(statistics.median(warm_times), 3),
                    "atlas_rgba_bytes": QImage(str(preview.atlas)).sizeInBytes(),
                    "atlas_png_bytes": preview.atlas.stat().st_size,
                    "raster_cache_limit_bytes": MAX_FRAME_CACHE * FRAME_WIDTH * FRAME_HEIGHT * 4,
                    "samples": len(cold_times),
                },
                indent=2,
            )
        )
    application.quit()


if __name__ == "__main__":
    main()
