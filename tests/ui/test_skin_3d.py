"""Skin 3D: UV trước/sau, lớp ngoài, legacy, cache hữu hạn và xoay thật qua QML."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPoint, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.ui.preview import open_preview
from nostalgia.ui.skin_frame_cache import MAX_FRAME_CACHE, SkinFrameCache
from nostalgia.ui.skin_mesh import normalize_skin, skin_surfaces
from nostalgia.ui.skin_renderer import render_skin
from nostalgia.ui.skin_sprite import ensure_skin_preview
from nostalgia.ui.worker import wait_for_background
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


def test_returning_account_shows_skin_on_first_page_load(preview: Preview) -> None:
    launcher, _first_view, _bridge, _root_item = preview
    launcher.add_offline_account("ReturningSkin")
    view, _second_bridge = open_preview(launcher)
    try:
        view.show()
        view.rootObject().setProperty("currentIndex", 3)
        figure = find_control(view.rootObject(), "accountSkinFigure")
        wait_until(lambda: bool(figure.property("atlasReady")))
    finally:
        wait_for_background()
        view.close()
        view.deleteLater()


def marked_skin() -> QImage:
    image = QImage(64, 64, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.fillRect(8, 8, 8, 8, QColor("red"))
    painter.fillRect(24, 8, 8, 8, QColor("blue"))
    painter.end()
    return image


def test_projection_uses_front_back_uv_and_preserves_overlay_alpha() -> None:
    texture = marked_skin()
    surfaces = skin_surfaces(texture, False)
    front = render_skin(surfaces, 0)
    back = render_skin(surfaces, 36)
    assert front.pixelColor(64, 45).red() > 200
    assert front.pixelColor(64, 45).blue() < 10
    assert back.pixelColor(64, 45).blue() > 200
    assert front.pixelColor(0, 0).alpha() == 0
    texture.setPixelColor(44, 12, QColor("lime"))
    overlay = render_skin(skin_surfaces(texture, False), 0)
    assert overlay != front, "mũ/lớp ngoài phải thực sự nằm trên mesh"


def test_slim_geometry_and_legacy_mirrored_limbs() -> None:
    texture = marked_skin()
    wide, slim = skin_surfaces(texture, False), skin_surfaces(texture, True)
    assert min(x for face in wide for x, _y, _z in face.vertices) == -8.25
    assert min(x for face in slim for x, _y, _z in face.vertices) == -7.25
    legacy = QImage(64, 32, QImage.Format.Format_ARGB32)
    legacy.fill(Qt.GlobalColor.transparent)
    legacy.setPixelColor(4, 20, QColor("red"))
    legacy.setPixelColor(7, 20, QColor("blue"))
    normalized = normalize_skin(legacy)
    assert normalized.size() == QSize(64, 64)
    assert normalized.pixelColor(20, 52).blue() == 255
    assert normalized.pixelColor(23, 52).red() == 255


def request_skin(provider: SkinFrameCache, skin_path: Path, frame_index: int) -> QImage:
    return provider.render(QUrl.fromLocalFile(str(skin_path)).toString(), False, frame_index)


def test_provider_bounds_cache_reuses_frames_and_invalidates_changed_texture(
    tmp_path: Path,
) -> None:
    skin_path = tmp_path / "skin with space.png"
    image = marked_skin()
    assert image.save(str(skin_path))
    provider = SkinFrameCache()
    first = request_skin(provider, skin_path, 0)
    assert request_skin(provider, skin_path, 0).cacheKey() == first.cacheKey()
    for frame_index in range(72):
        request_skin(provider, skin_path, frame_index)
    assert len(provider._frames) == MAX_FRAME_CACHE
    image.fill(QColor("yellow"))
    assert image.save(str(skin_path))
    assert request_skin(provider, skin_path, 0) != first


def test_invalid_or_remote_texture_uses_local_fallback(tmp_path: Path) -> None:
    provider = SkinFrameCache()
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"invalid")
    assert not request_skin(provider, broken, 0).isNull()
    assert not provider.render("https://example.invalid/skin.png", False, 0).isNull()


def test_atlas_cache_reopens_without_rendering_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skin_path = tmp_path / "skin.png"
    assert marked_skin().save(str(skin_path))
    renderer = SkinFrameCache()
    source = QUrl.fromLocalFile(str(skin_path)).toString()
    preview = ensure_skin_preview(tmp_path / "cache", renderer, source, False, "", True)
    assert preview.atlas is not None
    assert QImage(str(preview.atlas)).size() == QSize(1536, 1536)
    assert QImage(str(preview.thumbnail)).size() == QSize(128, 256)

    def unexpected_render(*_args: object) -> QImage:
        pytest.fail("đã cache thì không dựng hình lại")

    monkeypatch.setattr(renderer, "render", unexpected_render)
    assert ensure_skin_preview(tmp_path / "cache", renderer, source, False, "", True) == preview


def test_skin_drag_keyboard_and_hidden_window_stop_rendering(preview: Preview) -> None:
    _launcher, view, bridge, root_item = preview
    bridge.addOfflineAccount("SkinPreview")
    wait_until(lambda: bool(bridge.activePlayerName))
    root_item.setProperty("currentIndex", 3)
    figure = find_control(root_item, "accountSkinFigure")
    wait_until(lambda: bool(figure.property("atlasReady")))
    before = figure.property("frame")
    center = figure.mapToScene(QPoint(figure.width() / 2, figure.height() / 2)).toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(view, center + QPoint(65, 0))
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=center + QPoint(65, 0))
    wait_until(lambda: figure.property("frame") != before)
    before = figure.property("frame")
    figure.forceActiveFocus()
    QTest.keyClick(view, Qt.Key.Key_Right)
    QTest.qWait(300)
    assert figure.property("frame") != before
    view.hide()
    QTest.qWait(30)
    assert not figure.property("renderActive")
    view.show()
    wait_until(lambda: bool(figure.property("ready")))


def test_skin_library_skips_offscreen_previews_and_loads_on_scroll(
    preview: Preview, tmp_path: Path
) -> None:
    launcher, view, bridge, root_item = preview
    bridge.addOfflineAccount("SkinLibrary")
    wait_until(lambda: bool(bridge.activePlayerName))
    for number in range(24):
        skin_path = tmp_path / f"skin-{number}.png"
        texture = marked_skin()
        texture.setPixelColor(9, 9, QColor(number * 10, 100, 200))
        assert texture.save(str(skin_path))
        launcher.import_skin(skin_path)
    root_item.setProperty("currentIndex", 3)
    view.rootContext().contextProperty("accountBridge").libraryChanged.emit()
    QTest.qWait(150)
    grid = find_control(root_item, "skinLibraryGrid")
    cards = [card for card in grid.childItems() if "Rectangle" in card.metaObject().className()]
    figures = [find_control(card, "skinLibraryFigure") for card in cards]
    assert len(figures) == 24
    visible = [figure for figure in figures if figure.property("renderActive")]
    assert 0 < len(visible) < len(figures)
    wait_until(lambda: all(figure.property("ready") for figure in visible))
    scroll = find_control(root_item, "skinLibraryScroll")
    assert scroll.property("maxY") > 0
    scroll.scrollBy(float(scroll.property("maxY")), True)
    QTest.qWait(150)
    assert any(not figure.property("renderActive") for figure in visible)
    bottom = [figure for figure in figures if figure.property("renderActive")]
    assert bottom
    assert any(figure not in visible for figure in bottom)
    wait_until(lambda: all(figure.property("ready") for figure in bottom))
    skin_bridge = view.rootContext().contextProperty("skinPreviews")
    wait_until(lambda: not skin_bridge.busy)
    assert len(skin_bridge.atlases) == 1, "thẻ kho không được dựng atlas chuyển động riêng"
