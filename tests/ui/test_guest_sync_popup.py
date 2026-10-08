"""Khách xác nhận rủi ro, chọn nội dung trong popup mica thật ở hai cỡ màn hình."""

import base64
import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import find_control, press
from test_room_sync_ui import room_preview as room_preview

from nostalgia.api import Instance
from nostalgia.instance.sync_receipt import save_sync_receipt
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.sync_model import SyncFile

pytestmark = pytest.mark.usefixtures("qt_app")


def visual_control(parent: Any, name: str) -> Any:
    if parent.objectName() == name:
        return parent
    for child in parent.childItems():
        if found := visual_control(child, name):
            return found
    return None


def png_icon(color: str) -> str:
    bitmap = QImage(24, 24, QImage.Format.Format_ARGB32)
    bitmap.fill(QColor(color))
    for x in range(6, 18):
        for y in range(6, 18):
            bitmap.setPixelColor(x, y, QColor("#fafafa"))
    encoded = QByteArray()
    buffer = QBuffer(encoded)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    bitmap.save(buffer, "PNG")  # type: ignore[call-overload]  # PySide requires str at runtime.
    return "data:image/png;base64," + base64.b64encode(encoded.data()).decode("ascii")


def test_guest_selects_mods_and_texture_pack_before_install_in_glass_popup(
    room_preview: tuple[Any, ...], tmp_path: Path
) -> None:
    _launcher, gateway, view, root_item, multiplayer, sync_bridge, _bridge = room_preview
    warnings: list[str] = []
    view.engine().warnings.connect(
        lambda errors: warnings.extend(error.toString() for error in errors)
    )
    files = tuple(
        SyncFile(
            path, hashlib.sha256(b"fixture").hexdigest(), 7, title=title, icon_url=png_icon(color)
        )
        for path, title, color in [
            ("mods/sodium.jar", "Sodium", "#3b9877"),
            ("mods/private.jar", "Mod riêng của host", "#9f76ce"),
            ("mods/map.jar.disabled", "Bản đồ · Đang tắt", "#d3a73d"),
            ("resourcepacks/art.zip", "Texture pack của nhóm", "#4388b2"),
            ("shaderpacks/light.zip", "Shader pack", "#c46650"),
        ]
    )
    gateway.manifest = replace(gateway.manifest, files=files, pack_id="a" * 32, owner_id="host")
    multiplayer._apply_status(RoomStatus(role="joined", local_port=25566))
    wait_until(lambda: bool(sync_bridge.offer) and not sync_bridge.busy)
    press(view, find_control(root_item, "syncRoomPackButton"))
    popup = find_control(root_item, "guestSyncDialog")
    wait_until(lambda: popup.property("opened") and not sync_bridge.busy)
    assert not sync_bridge.confirmSync(False)
    assert not find_control(root_item, "guestSyncConfirm").property("clickable")
    mod_list = find_control(root_item, "guestSyncChoices")
    assert mod_list.property("count") == 3
    assert visual_control(mod_list, "syncContentMica") is not None
    checkbox = visual_control(mod_list, "selectSync_mods/private.jar")
    assert checkbox is not None
    press(view, checkbox)
    assert not next(
        choice["selected"]
        for choice in sync_bridge.guestChoices
        if choice["path"] == "mods/private.jar"
    )
    QTest.qWait(260)
    assert view.grabWindow().save(str(tmp_path / "guest-mod-selection.png"))
    press(view, visual_control(popup.property("contentItem"), "guestSyncTab-1"))
    wait_until(lambda: mod_list.property("count") == 1)
    press(view, visual_control(mod_list, "selectSync_resourcepacks/art.zip"))
    assert not next(
        choice["selected"]
        for choice in sync_bridge.guestChoices
        if choice["path"] == "resourcepacks/art.zip"
    )
    press(view, find_control(root_item, "guestSyncConsent"))
    assert popup.property("acknowledged")
    for scale, width, height in [(100, 1440, 900), (150, 1024, 600)]:
        view.resize(width, height)
        view.rootContext().contextProperty("settingsBridge").setAppearance(
            scale, False, False, True, "vi"
        )
        QTest.qWait(100)
        confirm = find_control(root_item, "guestSyncConfirm")
        origin = confirm.mapToScene(QPointF())
        assert origin.y() >= 0 and origin.y() + confirm.height() <= height
        assert origin.x() >= 0 and origin.x() + confirm.width() <= width
        assert popup.property("height") <= height - 48
    scroll = find_control(root_item, "guestSyncScroll")
    scroll.setProperty("contentY", scroll.property("maxY"))
    QTest.qWait(260)
    assert view.grabWindow().save(str(tmp_path / "guest-mod-selection-small.png"))
    multiplayer._apply_status(RoomStatus())
    assert not sync_bridge.reviewReady and not popup.property("acknowledged")
    assert not warnings


def test_previous_guest_instance_is_shown_and_new_mods_require_selection(
    room_preview: tuple[Any, ...],
) -> None:
    launcher, gateway, _view, root_item, multiplayer, sync_bridge, _bridge = room_preview
    gateway.manifest = replace(gateway.manifest, pack_id="a" * 32, owner_id="host")
    instance = launcher.create_instance(Instance("synced", "1.20.1", "Bản chơi của nhóm"))
    save_sync_receipt(launcher.paths, instance.instance_id, gateway.manifest, frozenset())
    gateway.manifest = replace(
        gateway.manifest,
        files=(
            *gateway.manifest.files,
            SyncFile("mods/new.jar", hashlib.sha256(b"new").hexdigest(), 3),
        ),
    )
    multiplayer._apply_status(RoomStatus(role="joined", local_port=25566))
    wait_until(lambda: bool(sync_bridge.offer) and not sync_bridge.busy)
    sync_bridge.sync()
    wait_until(lambda: sync_bridge.reviewReady and not sync_bridge.busy)
    assert sync_bridge.updateLabel == "Bản chơi của nhóm"
    assert not next(
        choice["selected"]
        for choice in sync_bridge.guestChoices
        if choice["path"] == "mods/new.jar"
    )
    assert (
        find_control(root_item, "guestSyncConfirm").property("label")
        == "Cập nhật bản chơi đã đồng bộ"
    )
