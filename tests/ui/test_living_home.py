"""Home giữ nút chơi rõ, cảnh không che nội dung; giảm chuyển động tắt toàn bộ animation."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import Q_ARG, QMetaObject, QPointF
from PySide6.QtTest import QTest
from test_main_window import Preview, find_control, press
from test_main_window import preview as preview  # fixture chung của preview
from test_payment_layout import assert_within

from nostalgia.api import Instance

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("scale", [100, 150])
def test_hero_content_and_action_fit_small_window(preview: Preview, scale: int) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    view.resize(1024, 600)
    settings = view.rootContext().contextProperty("settingsBridge")
    settings.setAppearance(scale, False, True, True, "vi")
    QTest.qWait(80)
    QTest.qWait(300)
    hero = find_control(root_item, "homeHero")
    play = find_control(root_item, "minimalPlay")
    diorama = find_control(root_item, "homeDiorama")
    copy = play.parentItem().parentItem()
    assert_within(copy, hero)
    assert_within(play, hero)
    copy_origin = copy.mapToItem(hero, QPointF())
    scene_origin = diorama.mapToItem(hero, QPointF())
    assert copy_origin.x() + copy.width() <= scene_origin.x()
    assert not diorama.property("animated")
    press(view, play)
    assert root_item.property("currentIndex") == 1


def test_motion_and_background_preferences_apply_immediately(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    settings = view.rootContext().contextProperty("settingsBridge")
    diorama = find_control(root_item, "homeDiorama")
    image = find_control(root_item, "homeIslandImage")
    assert image.implicitWidth() > 0
    view.requestActivate()
    QTest.qWait(120)
    if view.isActive():
        assert diorama.property("animated")
        QTest.qWait(200)
        assert diorama.property("bob") < 0
    settings.setAppearance(100, False, True, True, "vi")
    QTest.qWait(30)
    assert not diorama.property("animated")
    assert diorama.property("bob") == 0
    settings.setAppearance(100, False, False, False, "vi")
    QTest.qWait(30)
    assert not diorama.isVisible()
    assert not diorama.property("animated")


def test_play_block_is_first_on_home_without_turning_slides(preview: Preview) -> None:
    launcher, view, _bridge, root_item = preview
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("loginVisible", False)
    launcher.create_instance(Instance(instance_id="a", version_id="1.20.1", display_name="Alpha"))
    launcher.create_instance(Instance(instance_id="b", version_id="1.21.11", display_name="Beta"))
    _bridge.announce_instances_changed()
    QTest.qWait(300)
    hero = find_control(root_item, "homeHero")
    slides = find_control(root_item, "homeSlides")
    assert slides.property("current") == 0
    assert hero.mapToItem(None, QPointF()).y() < slides.mapToItem(None, QPointF()).y()
    play = find_control(root_item, "minimalPlay")
    assert play.isVisible() and play.height() >= 58
    pick = find_control(root_item, "homeInstancePick")
    assert pick.isVisible() and pick.property("count") == 2
    other = 1 - pick.property("currentIndex")
    name = pick.property("model")[other]
    QMetaObject.invokeMethod(pick, "activated", Q_ARG(int, other))
    QTest.qWait(50)
    assert hero.property("chosen")["label"] == name
