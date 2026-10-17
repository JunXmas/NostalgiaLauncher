"""Thẻ server Forgotten Worlds trên trang chủ và thông báo khi modpack có bản mới."""

from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QObject
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.api import Instance, Launcher
from nostalgia.content.builtin_receipt import BuiltinReceipt, save_builtin_receipt
from nostalgia.model.json_value import JsonValue
from nostalgia.storage.files import atomic_write_json
from nostalgia.ui.notifier import Notifier
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")

CHANNEL: dict[str, JsonValue] = {
    "format": 1,
    "preset": "forgotten-worlds",
    "version": "9.9.9",
    "minecraft": "1.21.11",
    "fabric-loader": "0.19.5",
    "url": "https://github.com/pack.mrpack",
    "sha256": "a" * 64,
    "size": 1,
}


def _home(root_item: Any) -> Any:
    root_item.setProperty("loginVisible", False)
    root_item.setProperty("currentIndex", 0)
    return find_control(root_item, "serverShowcase")


def _fw_instance(launcher: Launcher, pack_version: str) -> Instance:
    atomic_write_json(launcher.paths.version_json("1.21.11"), {"id": "1.21.11"})
    instance = launcher.create_instance(Instance("fw", "1.21.11", "Forgotten Worlds"))
    save_builtin_receipt(launcher.paths.instance_dir("fw"), BuiltinReceipt(pack_version, {}))
    return instance


def test_slides_switch_with_buttons(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    _home(root_item)
    slides = find_control(root_item, "homeSlides")
    assert slides.property("current") == 0
    press(view, find_control(slides, "homeSlidesNext"))
    wait_until(lambda: slides.property("current") == 1)
    press(view, find_control(slides, "homeSlidesNext"))
    wait_until(lambda: slides.property("current") == 0)
    press(view, find_control(slides, "homeSlidesPrev"))
    wait_until(lambda: slides.property("current") == 1)


def test_showcase_invites_to_create_without_server_instance(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    card = _home(root_item)
    action = find_control(card, "serverShowcaseAction")
    assert "Tạo" in action.property("label")
    press(view, action)
    dialog = find_control(root_item, "projectCreateInstance")
    wait_until(lambda: dialog.property("visible"))
    assert dialog.property("loaderKind") == "forgotten-worlds"


def test_showcase_joins_server_directly(preview: Preview, monkeypatch: pytest.MonkeyPatch) -> None:
    launcher, view, bridge, root_item = preview
    _fw_instance(launcher, "1.0.5")
    joined: list[tuple[str, str]] = []
    monkeypatch.setattr(type(bridge), "playServer", lambda _s, i, a: joined.append((i, a)))
    launcher.add_offline_account("Jun")
    bridge.announce_accounts_changed()
    bridge.announce_instances_changed()
    card = _home(root_item)
    action = find_control(card, "serverShowcaseAction")
    wait_until(lambda: "Vào server" in action.property("label"))
    press(view, action)
    wait_until(lambda: bool(joined))
    assert joined == [("fw", "snow.pikamc.vn:25079")]


def test_new_pack_shows_update_and_notifies_once(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, _view, bridge, root_item = preview
    _fw_instance(launcher, "1.0.5")

    def refresh(_self: Launcher) -> None:
        atomic_write_json(
            launcher.paths.updates_dir / "modpacks" / "forgotten-worlds.json", CHANNEL
        )

    monkeypatch.setattr(Launcher, "refresh_builtin_modpack", refresh)
    notes: list[tuple[str, str, str]] = []
    view_parent = bridge.parent()
    assert isinstance(view_parent, QObject)
    for notifier in view_parent.findChildren(Notifier):
        notifier.notified.connect(lambda k, t, d: notes.append((k, t, d)))
    found: list[str] = []
    bridge.modpackUpdateFound.connect(found.append)
    bridge.checkModpackUpdates()
    wait_until(lambda: bool(found) and not bridge.busy)
    assert found == ["9.9.9"]
    wait_until(lambda: any("9.9.9" in t for _k, t, _d in notes))
    card = _home(root_item)
    action = find_control(card, "serverShowcaseAction")
    wait_until(lambda: action.property("label") == "Cập nhật modpack")
    bridge.checkModpackUpdates()
    wait_until(lambda: not bridge.busy)
    assert found == ["9.9.9"]
