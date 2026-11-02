"""Cosmetic miễn phí lưu được; bản Plus chỉ xem thử và thống kê không hiện cho bạn bè."""

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import Instance
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_free_cosmetic_equips_but_plus_vector_stays_a_preview(
    social_preview: tuple[Any, ...],
    tmp_path: Path,
) -> None:
    _launcher, gateway, view, root_item, social, *_ = social_preview
    login_preview(social_preview)
    root_item.setProperty("currentIndex", 7)
    cosmetics = view.rootContext().contextProperty("cosmeticBridge")
    wait_until(lambda: cosmetics.details["loaded"] and not cosmetics.busy)
    page = find_control(root_item, "cosmeticLibrary")
    press(view, find_item(page, "profileDecor-sprout"))
    assert page.property("previewDecor") == "sprout"
    equip = find_control(root_item, "cosmeticEquip")
    assert equip.property("clickable")
    press(view, equip)
    wait_until(lambda: cosmetics.details["decor"] == "sprout" and not cosmetics.busy)
    assert gateway.profile_draft.decor == "sprout" and not social.account["plus"]
    QTest.qWait(80)
    assert view.grabWindow().save(str(tmp_path / "cosmetic-sprout.png"))
    press(view, find_item(page, "profileDecor-aurora-drift"))
    assert page.property("previewDecor") == "aurora-drift" and not equip.property("clickable")
    cosmetics.equip("aurora-drift")
    assert gateway.profile_draft.decor == "sprout"
    QTest.qWait(80)
    assert view.grabWindow().save(str(tmp_path / "cosmetic-aurora-preview.png"))


def test_play_statistics_remain_local_and_clear_when_opening_a_friend(
    social_preview: tuple[Any, ...],
) -> None:
    launcher, _gateway, view, root_item, _social, *_ = social_preview
    instance = launcher.create_instance(Instance("played", "1.21.11"))
    launcher.record_play_session(instance.instance_id, 0, 3600)
    login_preview(social_preview)
    press(view, find_control(root_item, "socialAccountToggle"))
    press(view, find_control(root_item, "openMyProfile"))
    profiles = view.rootContext().contextProperty("profileBridge")
    statistics = view.rootContext().contextProperty("profileStatsBridge")
    wait_until(lambda: statistics.details["available"] and not statistics.busy)
    assert statistics.details["playtime"] == "1 giờ" and statistics.details["launches"] == 1
    profiles.open("misa")
    wait_until(lambda: profiles.details.get("account_id") == "misa" and not profiles.busy)
    assert not statistics.details["available"]
