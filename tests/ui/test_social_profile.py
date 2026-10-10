"""Hồ sơ Qt thật: avatar mở đúng bạn, skin opt-in và đóng cửa sổ bỏ kết quả cũ."""

import base64
import hashlib
import threading
from pathlib import Path
from typing import Any, cast

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from nostalgia.errors import SocialError
from nostalgia.social.profile_model import SocialProfile
from nostalgia.ui.profile_media import cache_skin, publish_skin
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def test_friend_avatar_opens_read_only_profile_and_revoke_closes_it(
    social_preview: tuple[Any, ...],
) -> None:
    _launcher, gateway, view, root_item, _social, *_ = social_preview
    login_preview(social_preview)
    avatar = find_item(root_item, "friendAvatar-misa")
    assert avatar is not None
    center = avatar.mapToScene(QPointF(avatar.width() / 2, avatar.height() / 2)).toPoint()
    QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=center)
    modal = find_control(root_item, "socialProfileDialog")
    profiles = view.rootContext().contextProperty("profileBridge")
    wait_until(
        lambda: (
            modal.property("opened") and profiles.property("details").get("account_id") == "misa"
        )
    )
    assert not profiles.property("details")["mine"]
    assert not find_control(root_item, "editSocialProfile").property("visible")
    assert abs(modal.property("x") + modal.property("width") / 2 - view.width() / 2) < 2
    gateway.revoked = True
    _social.refresh()
    wait_until(lambda: not _social.signedIn)
    assert not modal.property("opened")
    assert profiles.property("details") == {}


def test_owner_shares_skin_without_changing_game_account_and_packs_opt_in(
    social_preview: tuple[Any, ...],
) -> None:
    launcher, gateway, view, root_item, _social, *_ = social_preview
    login_preview(social_preview)
    accounts_before = launcher.list_accounts()
    source = Path(__import__("nostalgia").__file__ or "").parent / "skin" / "defaults" / "steve.png"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    skin_entry = launcher.import_skin(source, name="Steve")
    accounts = view.rootContext().contextProperty("accountBridge")
    accounts.libraryChanged.emit()
    press(view, find_control(root_item, "socialAccountToggle"))
    press(view, find_control(root_item, "openMyProfile"))
    profiles = view.rootContext().contextProperty("profileBridge")
    wait_until(lambda: bool(profiles.property("details")) and not profiles.busy)
    assert not profiles.property("details")["skinFile"]
    press(view, find_control(root_item, "editSocialProfile"))
    find_control(root_item, "profileBio").setProperty("text", "Chơi cùng nhau")
    find_control(root_item, "shareProfileSkin").toggled.emit(True)
    choice = find_control(root_item, "profileSkinChoice")
    press(view, choice, Qt.Key.Key_Space)
    QTest.keyClick(view, Qt.Key.Key_Down)
    QTest.keyClick(view, Qt.Key.Key_Return)
    press(
        view,
        find_item(
            find_control(root_item, "socialProfileDialog").property("contentItem"),
            "profileAvatarMode-skin",
        ),
    )
    press(view, find_control(root_item, "saveSocialProfile"))
    wait_until(lambda: hasattr(gateway, "profile_draft") and not profiles.busy)
    assert gateway.profile_draft.bio == "Chơi cùng nhau"
    assert gateway.profile_draft.skin_png and gateway.profile_draft.avatar_png
    assert gateway.profile_draft.favorite_packs == ()
    assert launcher.list_accounts() == accounts_before
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    assert launcher.list_skin_library()[0].entry_id == skin_entry.entry_id
    wait_until(lambda: profiles.property("details")["skinFile"].startswith("file:"))
    figure = find_control(root_item, "profileSkin3D")
    assert abs(figure.property("height") - figure.property("width") * 2) < 1
    press(view, find_control(root_item, "editSocialProfile"))
    find_control(root_item, "shareProfileSkin").toggled.emit(False)
    press(view, find_control(root_item, "saveSocialProfile"))
    wait_until(lambda: not profiles.busy and gateway.profile_draft.skin_png == "")
    assert gateway.profile_draft.avatar_mode == "google"


def test_closed_profile_ignores_late_reply_and_invalid_skin_never_cached(
    social_preview: tuple[Any, ...], tmp_path: Path
) -> None:
    _launcher, gateway, view, _root_item, *_ = social_preview
    login_preview(social_preview)
    begun, finished = threading.Event(), threading.Event()
    original = gateway.fetch_profile

    def delayed(account_id: str) -> SocialProfile:
        begun.set()
        assert finished.wait(5)
        return cast(SocialProfile, original(account_id))

    gateway.fetch_profile = delayed
    profiles = view.rootContext().contextProperty("profileBridge")
    profiles.open("misa")
    assert begun.wait(2)
    profiles.close()
    finished.set()
    wait_until(lambda: not profiles.busy)
    assert profiles.property("details") == {}
    with pytest.raises(SocialError, match="hỏng"):
        cache_skin(tmp_path / "invalid-cache", "YQ==")
    assert not (tmp_path / "invalid-cache").exists()
    source = Path(__import__("nostalgia").__file__ or "").parent / "skin" / "defaults" / "steve.png"
    encoded, head = publish_skin(source.as_uri())
    assert encoded and head


def test_indexed_skin_avatar_includes_hat_overlay(tmp_path: Path) -> None:
    image = QImage(64, 64, QImage.Format.Format_Indexed8)
    image.setColorTable([QColor("red").rgba(), QColor("green").rgba()])
    image.fill(0)
    for x in range(40, 48):
        for y in range(8, 16):
            image.setPixel(x, y, 1)
    source = tmp_path / "indexed.png"
    assert image.save(str(source))
    _skin_png, head = publish_skin(source.as_uri())
    avatar = QImage.fromData(base64.b64decode(head))
    assert avatar.pixelColor(0, 0) == QColor("green")
