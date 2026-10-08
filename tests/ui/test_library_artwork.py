"""Cả bốn loại dùng ảnh đúng dự án; ô ngoài viewport giải phóng nguồn blur."""

from pathlib import Path

import pytest
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.api import Launcher
from nostalgia.content.model import ContentKind, Project, SearchPage
from qt_controls import find_control

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("content_kind", ["mod", "resourcepack", "modpack", "shader"])
def test_all_libraries_blur_correct_artwork_and_stop_outside_viewport(
    preview: Preview, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content_kind: ContentKind
) -> None:
    _launcher, view, _bridge, root_item = preview
    icon_file = tmp_path / "avatar.png"
    image = QImage(64, 64, QImage.Format.Format_ARGB32)
    image.fill(0xFF50B090)
    assert image.save(str(icon_file))
    projects = tuple(
        Project(
            f"demo-{position}",
            f"demo-{position}",
            f"Demo {position}",
            "Description",
            "Author",
            content_kind,
            icon_file.as_uri(),
            100,
            1,
            ("fabric",),
        )
        for position in range(18)
    )
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage(projects, 0, 18))
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 2)
    library = find_control(root_item, "minimalLibrary")
    library.setProperty("kind", content_kind)
    library.refresh()
    content = view.rootContext().contextProperty("contentBridge")
    wait_until(lambda: not content.searching and len(content.results) == 18)
    wait_until(lambda: find_item(root_item, "projectArtwork-demo-0") is not None)
    first = find_item(root_item, "projectArtwork-demo-0")
    last = find_item(root_item, "projectArtwork-demo-17")
    assert first is not None and last is not None
    wait_until(lambda: first.property("ready"))
    surface = find_control(first, "cardArtworkGlass")
    assert surface.property("blurRadius") == 32
    assert surface.property("blurOpacity") == pytest.approx(0.28)
    assert surface.property("backdrop") == find_control(first, "cardArtwork")
    assert not last.property("renderEnabled")
    assert find_control(last, "cardArtwork").property("source").isEmpty()
    assert find_control(first, "cardArtwork").property("sourceSize").width() <= 320
    scroll = find_control(root_item, "libraryScroll")
    scroll.scrollBy(float(scroll.property("maxY")), True)
    wait_until(lambda: last.property("ready"))
    assert not first.property("renderEnabled")
    assert find_control(first, "cardArtwork").property("source").isEmpty()
    library.setProperty("visible", False)
    QTest.qWait(60)
    assert not last.property("renderEnabled")
    assert find_control(last, "cardArtwork").property("source").isEmpty()
    library.setProperty("visible", True)
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        150, False, False, True, "vi"
    )
    scroll.scrollBy(-10000, True)
    QTest.qWait(100)
    metadata = find_item(root_item, "projectMeta-demo-0")
    action = find_item(root_item, "projectDownload-demo-0")
    description = find_item(root_item, "projectDescription-demo-0")
    assert metadata is not None and action is not None and description is not None
    assert metadata.x() + metadata.width() <= action.x()
    assert description.mapToItem(action, 0, description.height()).y() <= 0
