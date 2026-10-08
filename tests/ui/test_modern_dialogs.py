"""Các popup phụ vẫn đọc được và cuộn được khi chữ 150%, cửa sổ nhỏ."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from PySide6.QtTest import QTest
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from qt_controls import find_control, press, wheel

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize(
    "surface_name",
    ["AddAccountDialogSurface", "ModpackDialogSurface", "deviceLoginSurface", "loginCard"],
)
def test_mica_captures_page_instead_of_only_ambient(preview: Preview, surface_name: str) -> None:
    _launcher, _view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", surface_name != "loginCard")
    if surface_name == "AddAccountDialogSurface":
        root_item.setProperty("currentIndex", 3)
        find_control(root_item, "addAccountDialog").openDialog()
    elif surface_name == "ModpackDialogSurface":
        root_item.setProperty("currentIndex", 2)
        find_control(root_item, "modernQuickModpack").openFor("sample", "Sample pack")
    elif surface_name == "deviceLoginSurface":
        find_control(root_item, "minimalDeviceLogin").setProperty("visible", True)
    QTest.qWait(350)
    surface = find_control(root_item, surface_name)
    scene = find_control(root_item, "previewScene")
    assert surface.property("color").alphaF() < 0.85
    assert surface.property("backdrop") == scene
    effect = find_control(surface, "glassEffect")
    assert not effect.property("autoPaddingEnabled")
    ancestor = surface.parentItem()
    while ancestor:
        assert ancestor != scene, "A modal must not capture itself in its backdrop"
        ancestor = ancestor.parentItem()
    capture = effect.property("source")
    assert capture.property("sourceItem") == scene
    origin = surface.mapToItem(scene, 0, 0)
    rectangle = capture.property("sourceRect")
    assert rectangle.x() == pytest.approx(origin.x())
    assert rectangle.y() == pytest.approx(origin.y())
    assert rectangle.width() == pytest.approx(surface.width())


def test_add_account_error_and_two_factor_fit_small_window(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        150, False, False, True, "vi"
    )
    root_item.setProperty("currentIndex", 3)
    QTest.qWait(300)
    press(view, find_control(root_item, "addAccountButton"))
    dialog = find_control(root_item, "addAccountDialog")
    dialog.setProperty("mode", "ely")
    dialog.setProperty("needsTotp", True)
    dialog.setProperty("failure", "Thông báo xác thực cần đọc đầy đủ. " * 35)
    QTest.qWait(300)
    surface = find_control(root_item, "AddAccountDialogSurface")
    scroll = find_control(root_item, "accountFormScroll")
    assert surface.property("height") <= view.height() - 40
    assert surface.property("width") <= view.width() - 40
    assert scroll.property("maxY") > 0
    wheel(view, scroll)
    QTest.qWait(120)
    assert scroll.property("contentY") > 0
    assert find_control(root_item, "elySignInButton").property("visible")
    assert dialog.property("visible")


def test_quick_modpack_long_title_and_actions_remain_accessible(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 2)
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        150, False, False, True, "vi"
    )
    QTest.qWait(300)
    dialog = find_control(root_item, "modernQuickModpack")
    dialog.openFor("sample", "Bản chơi có tên rất dài " * 65)
    QTest.qWait(300)
    surface = find_control(root_item, "ModpackDialogSurface")
    scroll = find_control(root_item, "packFormScroll")
    assert surface.property("height") <= view.height() - 40
    assert surface.property("width") <= view.width() - 40
    assert scroll.property("maxY") > 0
    scroll.scrollBy(float(scroll.property("maxY")), True)
    QTest.qWait(30)
    action = find_control(root_item, "quickModpackInstall")
    assert action.property("visible")
    assert scroll.property("contentY") == pytest.approx(scroll.property("maxY"))
