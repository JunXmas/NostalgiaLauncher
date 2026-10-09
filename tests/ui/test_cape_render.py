"""Cape có UV và độ sâu sau lưng; đổi/gỡ cape không dùng nhầm atlas đã cache."""

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QImage

from nostalgia.ui.cape_mesh import cape_surfaces
from nostalgia.ui.skin_frame_cache import SkinFrameCache
from nostalgia.ui.skin_mesh import skin_surfaces
from nostalgia.ui.skin_renderer import render_skin
from nostalgia.ui.skin_sprite import ensure_skin_preview

pytestmark = pytest.mark.usefixtures("qt_app")


def textures() -> tuple[QImage, QImage]:
    skin = QImage(64, 64, QImage.Format.Format_ARGB32)
    skin.fill(QColor("#35bb6b"))
    cape = QImage(64, 32, QImage.Format.Format_ARGB32)
    cape.fill(QColor("#ff6633"))
    return skin, cape


def test_cape_is_behind_body_and_visible_when_rotated() -> None:
    skin, cape = textures()
    surfaces = skin_surfaces(skin, False) + cape_surfaces(cape)
    front, back = render_skin(surfaces, 0), render_skin(surfaces, 36)
    assert front.pixelColor(64, 125).green() > front.pixelColor(64, 125).red()
    assert back.pixelColor(64, 125).red() > back.pixelColor(64, 125).green()
    assert len(cape_surfaces(cape)) == 6


def test_cape_change_removal_and_texture_update_invalidate_cache(tmp_path: Path) -> None:
    skin, cape = textures()
    skin_path, cape_path = tmp_path / "skin.png", tmp_path / "cape.png"
    assert skin.save(str(skin_path)) and cape.save(str(cape_path))
    source, cape_source = (
        QUrl.fromLocalFile(str(skin_path)).toString(),
        QUrl.fromLocalFile(str(cape_path)).toString(),
    )
    renderer = SkinFrameCache()
    bare = renderer.render(source, False, 36)
    worn = renderer.render(source, False, 36, cape_source)
    assert worn != bare
    assert renderer.render(source, False, 36, cape_source).cacheKey() == worn.cacheKey()
    assert renderer.render(source, False, 36) == bare
    first = ensure_skin_preview(
        tmp_path / "cache", renderer, source, False, "", False, cape_source, 41
    )
    cape.fill(QColor("#5a71ff"))
    assert cape.save(str(cape_path))
    second = ensure_skin_preview(
        tmp_path / "cache", renderer, source, False, "", False, cape_source, 41
    )
    assert first.thumbnail != second.thumbnail and first.atlas is second.atlas is None
    assert renderer.render(source, False, 36, cape_source) != worn
