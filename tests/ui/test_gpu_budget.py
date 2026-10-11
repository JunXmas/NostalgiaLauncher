"""Thu hồi tài nguyên GPU khi chạy nền, giữ nguyên UI và phiên game/phòng."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QImage
from PySide6.QtQml import QQmlProperty
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_glass_grid_regression import open_library
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.ui.view import LauncherView
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


class ResourceCountingView(LauncherView):
    def __init__(self) -> None:
        super().__init__()
        self.release_calls = 0

    def releaseResources(self) -> None:
        self.release_calls += 1
        super().releaseResources()


def test_minimize_and_hide_release_graphics_without_recreating_qml(tmp_path: Path) -> None:
    page = tmp_path / "budget.qml"
    page.write_text('import QtQuick\nRectangle { property int selection: 7; color: "navy" }')
    view = ResourceCountingView()
    view.resize(300, 200)
    view.setSource(QUrl.fromLocalFile(str(page)))
    root_item = view.rootObject()
    assert root_item is not None
    view.show()
    wait_until(lambda: bool(view.effectsEnabled))
    assert not view.isPersistentGraphics() and not view.isPersistentSceneGraph()
    for _ in range(3):
        before = view.release_calls
        view.showMinimized()
        wait_until(lambda: not view.effectsEnabled)
        assert view.release_calls > before
        view.showNormal()
        wait_until(lambda: bool(view.effectsEnabled))
        assert view.rootObject() is root_item
        assert root_item.property("selection") == 7
    view.hide()
    assert not view.effectsEnabled
    view.show()
    wait_until(lambda: bool(view.effectsEnabled))
    assert view.rootObject() is root_item


def test_game_background_disables_blur_and_focus_restores_it(preview: Preview) -> None:
    _launcher, view, bridge, root_item = preview
    assert isinstance(view, LauncherView)
    root_item.setProperty("sessionSkipped", True)
    glass = find_control(root_item, "minimalNavigation")
    assert isinstance(glass, QObject)
    other = QQuickView()
    other.show()
    other.requestActivate()
    wait_until(lambda: not view.isActive())
    # Mở cửa sổ khác khi chưa chơi không làm mất mica.
    assert view.effectsEnabled and glass.property("graphicsEnabled")
    bridge._set_game_running(True)
    wait_until(lambda: not view.effectsEnabled)
    assert not glass.property("graphicsEnabled")
    assert view.isVisible() and bridge.gameRunning
    assert view.rootObject() is root_item
    view.requestActivate()
    wait_until(lambda: view.isActive() and bool(view.effectsEnabled))
    assert glass.property("graphicsEnabled")
    other.requestActivate()
    wait_until(lambda: not view.effectsEnabled)
    bridge._set_game_running(False)
    wait_until(lambda: bool(view.effectsEnabled))
    other.close()


def test_login_art_is_bounded_and_unloaded_after_entering_workspace(preview: Preview) -> None:
    _launcher, _view, _bridge, root_item = preview
    hero = find_control(root_item, "ambientHero")
    wait_until(lambda: hero.property("source").toString().endswith("hero.jpg"))
    assert 0 < hero.property("sourceSize").width() <= 2048
    root_item.setProperty("sessionSkipped", True)
    wait_until(lambda: not hero.property("source").toString())
    assert not root_item.property("loginVisible")


def test_background_game_keeps_skin_thumbnail_and_restores_rotation_atlas(preview: Preview) -> None:
    _launcher, view, bridge, root_item = preview
    bridge.addOfflineAccount("GpuPreview")
    wait_until(lambda: bool(bridge.activePlayerName))
    root_item.setProperty("currentIndex", 3)
    figure = find_control(root_item, "accountSkinFigure")
    wait_until(lambda: bool(figure.property("atlasReady")))
    atlas = find_control(figure, "skin3DAtlas")
    thumbnail = find_control(figure, "skin3DImage")
    other = QQuickView()
    other.show()
    other.requestActivate()
    wait_until(lambda: not view.isActive())
    bridge._set_game_running(True)
    wait_until(lambda: not atlas.property("source").toString())
    assert thumbnail.property("source").toString()
    assert figure.property("renderActive") and view.isVisible()
    view.requestActivate()
    wait_until(lambda: bool(figure.property("atlasReady")))
    assert atlas.property("source").toString()
    bridge._set_game_running(False)
    other.close()
    QTest.qWait(10)


def test_large_project_icons_are_decoded_at_their_display_size(
    preview: Preview, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, _view, _bridge, root_item = preview
    open_library(preview, monkeypatch)
    bitmap = QImage(2048, 2048, QImage.Format.Format_RGB32)
    bitmap.fill(0x204060)
    path = tmp_path / "large-icon.png"
    assert bitmap.save(str(path))
    card = find_control(root_item, "projectCard-demo-0")
    image = find_control(card, "projectIconImage")
    image.setProperty("source", QUrl.fromLocalFile(str(path)))
    wait_until(lambda: int(image.property("implicitWidth")) > 0)
    assert 0 < image.property("sourceSize").width() <= 256
    assert image.property("implicitWidth") <= 256
    assert image.property("implicitHeight") <= 256


def test_game_in_foreground_stops_scroll_until_the_launcher_is_used_again(preview: Preview) -> None:
    _launcher, view, bridge, root_item = preview
    assert isinstance(view, LauncherView)
    root_item.setProperty("sessionSkipped", True)
    scroll = find_control(root_item, "homeScroll")
    assert QQmlProperty(scroll, "contentHeight").write(2400)
    scroll.scrollBy(240, False)
    assert scroll.property("settling")
    other = QQuickView()
    other.show()
    other.requestActivate()
    wait_until(lambda: not view.isActive())
    bridge._set_game_running(True)
    wait_until(lambda: not scroll.property("settling"))
    paused = scroll.property("contentY")
    QTest.qWait(120)
    assert scroll.property("contentY") == paused
    view.requestActivate()
    wait_until(lambda: bool(view.effectsEnabled))
    scroll.scrollBy(120, False)
    assert scroll.property("settling")
    bridge._set_game_running(False)
    other.close()
