"""Slide Nos Client đầu trang chủ: ảnh/icon có trên đĩa, nút chính làm đúng việc theo bản chơi."""

import re
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6")
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview

from nostalgia.api import Instance
from nostalgia.storage.files import atomic_write_json
from qt_controls import find_control, press

pytestmark = pytest.mark.usefixtures("qt_app")

QML = Path(__file__).resolve().parents[2] / "src/nostalgia/ui/qml/preview/NosShowcase.qml"


def _slide(root_item: Any) -> Any:
    root_item.setProperty("loginVisible", False)
    root_item.setProperty("currentIndex", 0)
    find_control(root_item, "homeSlides").setProperty("current", 0)
    return find_control(root_item, "nosShowcase")


def test_every_icon_and_shot_the_slide_names_exists() -> None:
    # Ảnh thiếu thì Qt chỉ in cảnh báo rồi để trống ô — test là chỗ duy nhất bắt được.
    text = QML.read_text(encoding="utf-8")

    names = set(re.findall(r'icon: "([a-z]+)"', text)) | {"sky"}
    shots = re.findall(r'"\.\./assets/(nos/shot-[a-z]+\.jpg)"', text)
    asset_dir = QML.parent.parent / "assets"
    assert shots, "slide phải có ảnh chụp thật"
    for name in names:
        assert (asset_dir / "nos" / f"icon-{name}.png").is_file(), name
    for shot in shots:
        assert (asset_dir / shot).is_file(), shot


def test_nos_slide_comes_first(preview: Preview) -> None:
    _launcher, _view, _bridge, root_item = preview
    root_item.setProperty("loginVisible", False)
    root_item.setProperty("currentIndex", 0)
    assert find_control(root_item, "homeSlides").property("current") == 0
    assert find_control(root_item, "nosShowcase").property("active")


def test_action_turns_on_nos_for_a_supported_instance(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, view, bridge, root_item = preview
    fabric = "fabric-loader-0.19.3-1.21.11"
    for version_id, extra in (("1.21.11", {}), (fabric, {"inheritsFrom": "1.21.11"})):
        atomic_write_json(launcher.paths.version_json(version_id), {"id": version_id, **extra})
    launcher.create_instance(Instance("opt", fabric, "Optimized"))
    bridge.announce_instances_changed()
    toggled: list[tuple[str, bool]] = []
    monkeypatch.setattr(type(bridge), "toggleNosClient", lambda _s, i, on: toggled.append((i, on)))
    slide = _slide(root_item)
    action = find_control(slide, "nosShowcaseAction")
    wait_until(lambda: "Bật" in action.property("label"))
    press(view, action)
    wait_until(lambda: toggled == [("opt", True)])


def test_action_invites_to_create_without_a_supported_instance(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    slide = _slide(root_item)
    action = find_control(slide, "nosShowcaseAction")
    assert "Tạo" in action.property("label")
    press(view, action)
    wait_until(lambda: root_item.property("currentIndex") == 1)
