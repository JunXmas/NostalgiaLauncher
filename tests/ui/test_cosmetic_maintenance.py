"""Thêm/ẩn/vô hiệu hoá bằng danh mục, không sửa picker hoặc đường lưu."""

from dataclasses import replace
from typing import Any, cast

import pytest
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import ProfileDraft
from nostalgia.social.cosmetic import load_cosmetic_collection
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def managed_preview(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> tuple[Any, ...]:
    collection = load_cosmetic_collection()
    collection = replace(
        collection,
        revision=2,
        sets=(
            collection.sets[0],
            replace(collection.sets[1], state="retired"),
            replace(collection.sets[2], state="disabled"),
            replace(collection.sets[0], key="moonlight", name="Moonlight"),
        ),
    )
    monkeypatch.setattr("nostalgia.ui.cosmetic_bridge.load_cosmetic_collection", lambda: collection)
    return cast(tuple[Any, ...], request.getfixturevalue("social_preview"))


def test_new_set_appears_and_saves_without_changing_qml(managed_preview: tuple[Any, ...]) -> None:
    _launcher, gateway, view, root_item, *_ = managed_preview
    gateway.snapshot = replace(
        gateway.snapshot,
        account=replace(
            gateway.snapshot.account, plus_until=4_000_000_000, plus_plan="plus-month-v1"
        ),
    )
    login_preview(managed_preview)
    root_item.setProperty("currentIndex", 7)
    cosmetics = view.rootContext().contextProperty("cosmeticBridge")
    wait_until(lambda: cosmetics.property("details")["loaded"] and not cosmetics.busy)
    page = find_control(root_item, "cosmeticLibrary")
    assert cosmetics.property("revision") == 2
    assert find_item(page, "profileDecor-emerald") is None
    assert find_item(page, "profileDecor-amber") is None
    press(view, find_item(page, "profileDecor-moonlight"))
    press(view, find_control(page, "cosmeticEquip"))
    wait_until(lambda: cosmetics.property("details")["decor"] == "moonlight")
    cosmetics.equip("emerald")
    cosmetics.equip("amber")
    assert gateway.profile_draft.decor == "moonlight"


@pytest.mark.parametrize("saved", ["emerald", "amber", "future-uninstalled"])
def test_existing_profiles_render_retired_and_fall_back_safely(
    managed_preview: tuple[Any, ...], saved: str
) -> None:
    _launcher, gateway, view, root_item, *_ = managed_preview
    gateway.profile_draft = ProfileDraft(decor=saved)
    login_preview(managed_preview)
    root_item.setProperty("currentIndex", 7)
    cosmetics = view.rootContext().contextProperty("cosmeticBridge")
    wait_until(lambda: cosmetics.property("details")["loaded"] and not cosmetics.busy)
    page = find_control(root_item, "cosmeticLibrary")
    avatar = find_control(page, "socialAvatarFrame")
    QTest.qWait(60)
    assert avatar.property("decorated") == (saved == "emerald")
    assert bool(avatar.property("source").toString()) == (saved == "emerald")
    cosmetics.equip("none")
    wait_until(lambda: cosmetics.property("details")["decor"] == "none" and not cosmetics.busy)
    assert gateway.profile_draft.decor == "none"
