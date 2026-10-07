"""Cosmetic thật: xem thử không mở khóa, lưu Pro và ảnh trong suốt có giới hạn."""

import base64
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_social_ui import login_preview
from test_social_ui import social_preview as social_preview

from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")


def open_editor(preview: tuple):
    _launcher, _gateway, view, root_item, *_ = preview
    press(view, find_control(root_item, "socialAccountToggle"))
    press(view, find_control(root_item, "openMyProfile"))
    profiles = view.rootContext().contextProperty("profileBridge")
    wait_until(lambda: bool(profiles.property("details")) and not profiles.busy)
    press(view, find_control(root_item, "editSocialProfile"))
    return find_control(root_item, "socialProfileDialog"), profiles


def test_free_preview_never_equips_and_cancel_restores_saved_appearance(
    social_preview: tuple,
) -> None:
    _launcher, gateway, view, root_item, social, *_ = social_preview
    login_preview(social_preview)
    assert not social.account["profilePlus"]
    dialog, profiles = open_editor(social_preview)
    choice = find_item(dialog.property("contentItem"), "profileDecor-amber")
    press(view, choice)
    banner = find_control(dialog, "profileBanner")
    avatar = find_control(dialog, "profileAvatar")
    assert banner.property("decor") == avatar.property("decor") == "amber"
    assert choice.property("previewed") and not choice.property("selected")
    press(view, find_control(root_item, "saveSocialProfile"))
    wait_until(lambda: hasattr(gateway, "profile_draft") and not profiles.busy)
    assert gateway.profile_draft.decor == "none"
    assert banner.property("decor") == avatar.property("decor") == "none"
    press(view, find_control(root_item, "editSocialProfile"))
    press(view, find_item(dialog.property("contentItem"), "profileDecor-emerald"))
    press(view, find_control(root_item, "cancelSocialProfileEdit"))
    assert banner.property("decor") == "none"
    assert gateway.profile_draft.decor == "none"


@pytest.mark.parametrize("decor", ["amethyst", "emerald", "amber"])
def test_pro_saves_matching_banner_and_frame_and_hides_image_on_close(
    social_preview: tuple, decor: str
) -> None:
    _launcher, gateway, view, root_item, social, *_ = social_preview
    gateway.snapshot = replace(
        gateway.snapshot,
        account=replace(
            gateway.snapshot.account, plus_until=4_000_000_000, plus_plan="plus-half-year-v1"
        ),
    )
    login_preview(social_preview)
    assert social.account["profilePlus"]
    dialog, profiles = open_editor(social_preview)
    choice = find_item(dialog.property("contentItem"), "profileDecor-" + decor)
    press(view, choice)
    assert choice.property("selected")
    press(view, find_control(root_item, "saveSocialProfile"))
    wait_until(lambda: hasattr(gateway, "profile_draft") and not profiles.busy)
    assert gateway.profile_draft.decor == decor
    assert find_control(dialog, "profileBanner").property("decor") == decor
    frame = find_control(find_control(dialog, "profileAvatar"), "socialAvatarFrame")
    wait_until(lambda: frame.property("ready"))
    assert frame.property("sourceSize").width() <= 384
    banner_image = find_control(find_control(dialog, "profileBanner"), "cosmeticBannerImage")
    wait_until(lambda: find_control(dialog, "profileBanner").property("ready"))
    assert banner_image.property("sourceSize").width() <= 1536
    dialog.close()
    wait_until(lambda: frame.property("source").isEmpty())
    assert banner_image.property("source").isEmpty()


def test_production_frames_leave_the_avatar_center_transparent() -> None:
    import nostalgia

    cosmetic_dir = Path(nostalgia.__file__).parent / "ui/qml/assets/cosmetics"
    for name in ("amethyst", "grove", "eclipse"):
        frame = QImage(str(cosmetic_dir / f"{name}-frame.png"))
        assert not frame.isNull() and frame.hasAlphaChannel()
        assert frame.width() == frame.height()
        for x, y in ((0, 0), (0.5, 0.5), (0.4, 0.5), (0.6, 0.5), (0.5, 0.4)):
            assert frame.pixelColor(int(x * frame.width()), int(y * frame.height())).alpha() == 0
        banner = QImage(str(cosmetic_dir / f"{name}-banner.png"))
        assert not banner.isNull() and banner.width() == banner.height() * 3


def test_loaded_avatar_and_banner_actually_render_pixels(
    social_preview: tuple, tmp_path: Path
) -> None:
    _launcher, gateway, view, _root_item, *_ = social_preview
    image = QImage(8, 8, QImage.Format.Format_ARGB32)
    image.fill(0xFFFF0000)
    avatar_file = tmp_path / "avatar.png"
    assert image.save(str(avatar_file))
    gateway.snapshot = replace(
        gateway.snapshot,
        account=replace(
            gateway.snapshot.account,
            avatar_url="data:image/png;base64,"
            + base64.b64encode(avatar_file.read_bytes()).decode(),
        ),
    )
    login_preview(social_preview)
    dialog, _profiles = open_editor(social_preview)
    press(view, find_item(dialog.property("contentItem"), "profileDecor-amethyst"))
    banner = find_control(dialog, "profileBanner")
    wait_until(lambda: banner.property("ready"))
    QTest.qWait(350)
    screenshot = view.grabWindow()

    def pixel(control, x: float, y: float):
        position = control.mapToScene(QPointF(control.width() * x, control.height() * y))
        dpr = screenshot.devicePixelRatio()
        return screenshot.pixelColor(round(position.x() * dpr), round(position.y() * dpr))

    avatar = find_control(dialog, "profileAvatar")
    center = pixel(avatar, 0.5, 0.5)
    assert center.red() > 240 and center.green() < 20 and center.blue() < 20
    if avatar.property("shaderAvailable"):
        corner = pixel(avatar, 0.2, 0.2)
        assert not (corner.red() > 240 and corner.green() < 20 and corner.blue() < 20)
    colors = [pixel(banner, x / 100, y / 100) for x in range(70, 96, 5) for y in (20, 50, 80)]
    assert max(c.red() for c in colors) - min(c.red() for c in colors) > 20
