"""Bấm Chơi trên thẻ bản chơi: hiện cửa sổ chọn (tab mở sẵn là nơi chơi gần nhất), bấm thẻ world /
server thì vào thẳng nơi đó; bản chơi không có gì để chọn thì mở game luôn như trước."""

from __future__ import annotations

import base64
import json
import os
import time
from typing import Any

import pytest

pytest.importorskip("PySide6")
from test_bridges import wait_until
from test_main_window import Preview
from test_main_window import preview as preview

from nbt_fixture import tiny_png, write_servers, write_world
from nostalgia.api import Launcher
from nostalgia.instance.model import Instance
from qt_controls import find_control, press
from version_fixtures import load_fixture

pytestmark = pytest.mark.usefixtures("qt_app")

ICON = base64.b64encode(tiny_png()).decode()


class FakeGame:
    def wait(self, _timeout: float | None = None) -> int:
        return 0


def stub_launch(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    launches: list[dict[str, Any]] = []

    def fake_launch(_self: Launcher, instance_id: str, _account_id: str, **kwargs: Any) -> FakeGame:
        launches.append({**kwargs, "instance_id": instance_id})
        return FakeGame()

    monkeypatch.setattr(Launcher, "launch_instance", fake_launch)
    monkeypatch.setattr(Launcher, "install_version", lambda *_args, **_kwargs: None)
    return launches


def seed(
    context: Preview,
    *,
    worlds: int,
    servers: int,
    servers_newer: bool = False,
    version_id: str = "1.21.4",
) -> None:
    launcher, _view, bridge, root_item = context
    launcher.add_offline_account("Jun")
    path = launcher.paths.version_json(version_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(load_fixture(version_id)), encoding="utf-8")
    instance = launcher.create_instance(Instance(instance_id="van", version_id=version_id))
    game_dir = launcher.instance_game_dir(instance)
    now_ms = int(time.time() * 1000)
    for number in range(worlds):
        write_world(game_dir, f"w{number}", f"Thế giới {number}", now_ms - 3_600_000 * (number + 1))
    if servers:
        servers_path = write_servers(
            game_dir, [(f"Server {n}", f"s{n}.example", ICON, False) for n in range(servers)]
        )
        moment = time.time() - (0 if servers_newer else 86_400)
        os.utime(servers_path, (moment, moment))
    bridge.announce_accounts_changed()
    bridge.announce_instances_changed()
    root_item.setProperty("sessionSkipped", True)
    root_item.setProperty("currentIndex", 1)


def click_play(context: Preview) -> Any:
    _launcher, view, _bridge, root_item = context
    wait_until(lambda: find_visible(root_item, "instanceAction-van") is not None)
    press(view, find_visible(root_item, "instanceAction-van"))
    return find_control(root_item, "playChoiceDialog")


def find_visible(root_item: Any, name: str) -> Any:
    """Duyệt cây hình từ gốc CỬA SỔ: popup nằm trong Overlay, không nằm dưới item gốc."""
    pending = [root_item.window().contentItem()]
    while pending:
        node = pending.pop()
        if node.objectName() == name and node.isVisible():
            return node
        pending.extend(node.childItems())
    return None


def test_choosing_a_world_enters_it(preview: Preview, monkeypatch: pytest.MonkeyPatch) -> None:
    launches = stub_launch(monkeypatch)
    seed(preview, worlds=3, servers=1)
    dialog = click_play(preview)
    wait_until(lambda: bool(dialog.property("opened")))
    assert dialog.property("tab") == 0, "world chơi gần hơn servers.dat → mở tab Singleplayer"
    _launcher, view, _bridge, root_item = preview
    wait_until(lambda: find_visible(root_item, "playWorld-w1") is not None)
    press(view, find_visible(root_item, "playWorld-w1"))
    wait_until(lambda: len(launches) == 1)
    assert (launches[0]["instance_id"], launches[0]["world_folder"]) == ("van", "w1")
    assert not dialog.property("opened")


def test_multiplayer_tab_opens_first_and_enters_a_server(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    launches = stub_launch(monkeypatch)
    seed(preview, worlds=2, servers=2, servers_newer=True)
    dialog = click_play(preview)
    wait_until(lambda: bool(dialog.property("opened")))
    assert dialog.property("tab") == 1, "servers.dat mới sửa hơn world → mở tab Multiplayer"
    _launcher, view, _bridge, root_item = preview
    wait_until(lambda: find_visible(root_item, "playServer-s1.example") is not None)
    press(view, find_visible(root_item, "playServer-s1.example"))
    wait_until(lambda: len(launches) == 1)
    assert launches[0]["server_address"] == "s1.example" and launches[0]["world_folder"] == ""


def test_just_play_and_empty_instances_open_the_game_as_before(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    launches = stub_launch(monkeypatch)
    seed(preview, worlds=1, servers=0)
    dialog = click_play(preview)
    wait_until(lambda: bool(dialog.property("opened")))
    _launcher, view, bridge, root_item = preview
    press(view, find_control(root_item, "playChoiceJustPlay"))
    wait_until(lambda: len(launches) == 1 and not bridge.busy)
    assert launches[0]["world_folder"] == "" and launches[0]["server_address"] == ""

    world = preview[0].instance_game_dir(preview[0].list_instances()[0]) / "saves" / "w0"
    (world / "level.dat").unlink()
    click_play(preview)
    wait_until(lambda: len(launches) == 2 and not bridge.busy)
    assert not dialog.property("opened"), "không có gì để chọn thì không hiện cửa sổ"
    assert launches[1]["world_folder"] == "" and launches[1]["server_address"] == ""


def test_versions_without_quick_play_skip_the_world_tab(
    preview: Preview, monkeypatch: pytest.MonkeyPatch
) -> None:
    """1.12.2 không vào thẳng được thế giới: chọn world cũng chỉ mở game, nên bản chỉ có world
    thì không bày cửa sổ ra mà mở game luôn."""
    launches = stub_launch(monkeypatch)
    seed(preview, worlds=2, servers=0, version_id="1.12.2")
    dialog = click_play(preview)
    _launcher, _view, bridge, _root_item = preview
    wait_until(lambda: len(launches) == 1 and not bridge.busy)
    assert not dialog.property("opened") and launches[0]["world_folder"] == ""
