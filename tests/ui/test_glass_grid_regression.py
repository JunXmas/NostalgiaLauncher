"""Ảnh chụp thật bắt mask trắng; hình học bắt lưới xuống dòng sớm và chữ chồng nút."""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_instance_library import browse, prepare
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.api import Instance, Launcher
from nostalgia.content.model import Project, SearchPage
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


def open_library(context: Preview, monkeypatch: pytest.MonkeyPatch) -> None:
    _launcher, view, _bridge, root_item = context
    projects = tuple(
        Project(
            f"demo-{position}",
            f"demo-{position}",
            "Modpack with a long title",
            "A long description that wraps across multiple lines "
            "and must leave the install button accessible.",
            "Author",
            "modpack",
            "",
            20000,
            1,
            ("fabric",),
        )
        for position in range(24)
    )
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage(projects, 0, 24))
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 2)
    content = view.rootContext().contextProperty("contentBridge")
    wait_until(lambda: not content.searching and len(content.results) == 24)
    wait_until(lambda: find_item(root_item, "projectCard-demo-0") is not None)
    QTest.qWait(100)


def background_color(view: QQuickView, control: QQuickItem) -> QColor:
    frame = view.grabWindow()
    assert not frame.isNull()
    point = control.mapToScene(QPointF(control.width() - 12, control.height() / 2))
    dpr = frame.devicePixelRatio()
    return frame.pixelColor(round(point.x() * dpr), round(point.y() * dpr))


def test_glass_has_no_white_mask_with_missing_artwork_or_unfrosted_tip(
    preview: Preview, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, view, _bridge, root_item = preview
    open_library(preview, monkeypatch)
    artwork = find_control(root_item, "projectArtwork-demo-0")
    surface = find_control(artwork, "cardArtworkGlass")
    image = QImage(32, 32, QImage.Format.Format_ARGB32)
    image.fill(0xFF203050)
    icon = tmp_path / "icon.png"
    assert image.save(str(icon))
    for source, ready in [
        ("", False),
        (icon.as_uri(), True),
        ((tmp_path / "missing.png").as_uri(), False),
        ("", False),
    ]:
        artwork.setProperty("source", source)

        def matches_ready(expected: bool = ready) -> bool:
            return bool(artwork.property("ready")) == expected

        wait_until(matches_ready)
        QTest.qWait(120)
        assert background_color(view, surface).lightness() < 160
        assert not find_control(surface, "glassMask").property("visible")
    dialog = find_control(root_item, "guideDialog")
    dialog.openFor("create")
    wait_until(lambda: dialog.property("opened"))
    QTest.qWait(200)
    tip = find_control(root_item, "guideTipSurface")
    assert not tip.property("frosted")
    assert background_color(view, tip).lightness() < 160
    dialog.close()


@pytest.mark.parametrize(
    "width,height,scale", [(1440, 900, 100), (1920, 1080, 125), (1024, 600, 150)]
)
@pytest.mark.parametrize("language", ["en", "vi"])
def test_library_and_instances_use_every_column_without_text_overlap(
    preview: Preview,
    monkeypatch: pytest.MonkeyPatch,
    width: int,
    height: int,
    scale: int,
    language: str,
) -> None:
    launcher, view, bridge, root_item = preview
    view.resize(width, height)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, True, False, language
    )
    open_library(preview, monkeypatch)
    scroll = find_control(root_item, "libraryScroll")
    columns = int(scroll.property("columns"))
    cards: list[QQuickItem] = []
    for position in range(columns):
        card = find_item(root_item, f"projectCard-demo-{position}")
        assert card is not None
        cards.append(card)
    points = [card.mapToItem(scroll, 0, 0) for card in cards]
    assert all(point.y() == pytest.approx(points[0].y()) for point in points)
    assert points[-1].x() + cards[-1].width() > scroll.width() - 40
    assert points[-1].x() + cards[-1].width() <= scroll.width()
    description = find_control(root_item, "projectDescription-demo-0")
    button = find_control(root_item, "projectDownload-demo-0")
    assert description.mapToItem(button, 0, description.height()).y() <= -4
    for position in range(10):
        launcher.save_instance(Instance(f"grid-{position}", "1.21.1", f"World {position}"))
    bridge.announce_instances_changed()
    root_item.setProperty("currentIndex", 1)
    QTest.qWait(200)
    instances = find_control(root_item, "instancesScroll")
    columns = int(instances.property("columns"))
    page = find_control(root_item, "minimalInstances")
    actions = [find_control(page, f"instanceAction-grid-{position}") for position in range(columns)]
    positions = [action.mapToItem(instances, 0, 0) for action in actions]
    # Hover làm thẻ phóng nhẹ 0,8%; không coi chuyển động đó là xuống hàng.
    assert all(abs(point.y() - positions[0].y()) < 3 for point in positions), positions
    assert positions[-1].x() + actions[-1].width() > instances.width() - 110


def test_compact_library_description_and_scaled_guide_do_not_overlap(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    _launcher, view, _bridge, root_item = preview
    prepare(preview, monkeypatch)
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        150, False, True, False, "en"
    )
    dialog = browse(preview)
    content = view.rootContext().contextProperty("contentBridge")
    content._results_model.reset(
        [
            replace(
                content._results_model.projects[0],
                description="A long description that would otherwise push "
                "the second line into the install button.",
            )
        ]
    )
    QTest.qWait(150)
    scope = dialog.property("contentItem")
    description = find_control(scope, "projectDescription-demo")
    button = find_control(scope, "projectDownload-demo")
    assert description.mapToItem(button, 0, description.height()).y() <= -4
    guide = find_control(root_item, "guideDialog")
    guide.openFor("create")
    wait_until(lambda: guide.property("opened"))
    QTest.qWait(100)
    assert find_control(root_item, "guideWalkthrough").property("columns") == 1
    assert guide.property("height") <= view.height() - 40
    guide.close()
