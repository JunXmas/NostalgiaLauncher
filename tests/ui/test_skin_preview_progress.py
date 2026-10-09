"""Đổi dáng tay có thumbnail ngay, không chờ render hết atlas xoay."""

import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage
from test_bridges import wait_until

from nostalgia.ui import skin_preview_bridge
from nostalgia.ui.skin_frame_cache import SkinFrameCache
from nostalgia.ui.skin_preview_bridge import SkinPreviewBridge
from nostalgia.ui.skin_sprite import SkinPreview, ensure_skin_preview

pytestmark = pytest.mark.usefixtures("qt_app")


def test_thumbnail_is_published_before_background_atlas_finishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "skin.png"
    texture = QImage(64, 64, QImage.Format.Format_ARGB32)
    texture.fill(0xFF548ED4)
    assert texture.save(str(path))
    release = threading.Event()

    def delayed_atlas(
        cache_dir: Path,
        renderer: SkinFrameCache,
        source: str,
        slim: bool,
        revision: str,
        animated: bool,
        cape_source: str,
        preview_frame: int,
    ) -> SkinPreview:
        if animated:
            assert release.wait(4)
        return ensure_skin_preview(
            cache_dir, renderer, source, slim, revision, animated, cape_source, preview_frame
        )

    monkeypatch.setattr(skin_preview_bridge, "ensure_skin_preview", delayed_atlas)
    bridge = SkinPreviewBridge(tmp_path)
    bridge.ensurePreview(QUrl.fromLocalFile(str(path)).toString(), True, "", True)
    try:
        wait_until(lambda: bool(bridge.previews))
        assert bridge.busy and not bridge.atlases
    finally:
        release.set()
    wait_until(lambda: bool(bridge.atlases) and not bridge.busy)
