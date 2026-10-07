"""Cosmetic library: preview, one equipped set and unrelated profile preservation."""

from dataclasses import replace
from typing import Any

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.api import ProfileDraft
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.mark.parametrize("paid", [False, True])
def test_library_preview_and_equip_preserve_latest_profile(
    social_preview: tuple[Any, ...], paid: bool
) -> None:
    _launcher, gateway, view, root_item, social, *_ = social_preview
    if paid:
        gateway.snapshot = replace(
            gateway.snapshot,
            account=replace(
                gateway.snapshot.account, plus_until=4_000_000_000, plus_plan="plus-month-v1"
            ),
        )
    login_preview(social_preview)
    root_item.setProperty("currentIndex", 7)
    cosmetics = view.rootContext().contextProperty("cosmeticBridge")
    wait_until(lambda: cosmetics.property("details")["loaded"] and not cosmetics.busy)
    page = find_control(root_item, "cosmeticLibrary")
    press(view, find_item(page, "profileDecor-amethyst"))
    assert page.property("previewDecor") == "amethyst"
    assert not hasattr(gateway, "profile_draft")
    equip = find_control(root_item, "cosmeticEquip")
    assert equip.property("clickable") == paid
    # A profile edit after loading the library must survive equipping cosmetic.
    gateway.profile_draft = ProfileDraft(bio="Vừa sửa giới thiệu", avatar_mode="initials")
    cosmetics.equip("amethyst")
    if paid:
        wait_until(
            lambda: cosmetics.property("details")["decor"] == "amethyst" and not cosmetics.busy
        )
        assert cosmetics.property("details")["decor"] == "amethyst"
    else:
        QTest.qWait(80)
        assert gateway.profile_draft.decor == "none"
    assert gateway.profile_draft.bio == "Vừa sửa giới thiệu"
    assert gateway.profile_draft.avatar_mode == "initials"
    cosmetics.equip("unknown")
    assert not cosmetics.busy
    social.signOut()
    wait_until(lambda: not social.signedIn)
    assert not cosmetics.property("details")["loaded"]


def test_own_avatar_opens_profile_and_logout_confirms_without_removing_minecraft(
    social_preview: tuple[Any, ...],
) -> None:
    launcher, _gateway, view, root_item, social, *_ = social_preview
    login_preview(social_preview)
    accounts_before = launcher.list_accounts()
    avatar = find_control(root_item, "ownProfileAvatar")
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, pos=avatar.mapToScene(QPointF(16, 16)).toPoint()
    )
    modal = find_control(root_item, "socialProfileDialog")
    profiles = view.rootContext().contextProperty("profileBridge")
    wait_until(lambda: modal.property("opened") and profiles.property("details").get("mine"))
    modal.close()
    QTest.qWait(150)
    press(view, find_control(root_item, "socialAccountToggle"))
    press(view, find_control(root_item, "socialLogout"))
    confirm = find_control(root_item, "confirmationModal")
    wait_until(lambda: confirm.property("opened"))
    assert social.signedIn
    press(view, find_control(root_item, "confirmCancel"))
    assert social.signedIn
    press(view, find_control(root_item, "socialAccountToggle"))
    press(view, find_control(root_item, "socialLogout"))
    wait_until(lambda: confirm.property("opened"))
    press(view, find_control(root_item, "confirmAccept"))
    wait_until(lambda: not social.signedIn and not social.busy)
    assert launcher.list_accounts() == accounts_before
