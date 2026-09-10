"""Nhóm SERVER trong ô CHƠI TIẾP: hàng đúng khoá và chỉ quét lại khi bản chơi đổi / game tắt;
`playServer` đưa địa chỉ xuống façade; QML vẽ tối đa 3 nút có icon thật và bấm là vào server."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_continue_card import collect_items, seed, stub_launch
from test_home_layout import find_item
from test_qml import make_launcher

from nbt_fixture import tiny_png, write_servers
from nostalgia.api import Launcher
from nostalgia.ui.app import build_view
from nostalgia.ui.bridge import LauncherBridge

pytestmark = pytest.mark.usefixtures("qt_app")

ICON = base64.b64encode(tiny_png()).decode()
SERVER_KEYS = {"instanceId", "instanceLabel", "serverName", "address", "iconUrl"}


def seed_servers(launcher: Launcher, *, count: int = 2) -> None:
    seed(launcher)
    instance = next(i for i in launcher.list_instances() if i.instance_id == "van")
    write_servers(
        launcher.instance_game_dir(instance),
        [
            (f"Server {n}", f"s{n}.example:25565", ICON if n == 0 else None, False)
            for n in range(count)
        ],
    )


def test_rows_are_cached_and_refreshed_with_the_worlds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    seed_servers(launcher)
    scans: list[int] = []
    original = Launcher.list_recent_servers

    def counted(self: Launcher, **kwargs: Any) -> Any:
        scans.append(1)
        return original(self, **kwargs)

    monkeypatch.setattr(Launcher, "list_recent_servers", counted)
    bridge = LauncherBridge(launcher)
    rows = bridge.recentServers
    assert [row["serverName"] for row in rows] == ["Server 0", "Server 1"]
    assert set(rows[0]) == SERVER_KEYS
    assert rows[0]["address"] == "s0.example:25565" and rows[0]["instanceLabel"] == "Vanilla"
    assert rows[0]["iconUrl"].startswith("data:image/png;base64,") and rows[1]["iconUrl"] == ""
    again = [bridge.recentServers for _ in range(5)]
    assert scans == [1] and len(again) == 5
    bridge.instancesChanged.emit()
    after_change = bridge.recentServers
    bridge.gameStopped.emit(0)
    after_stop = bridge.recentServers
    assert len(scans) == 3 and len(after_change) == len(after_stop) == 2


def test_play_server_hands_the_address_to_the_facade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    seed_servers(launcher)
    launcher.add_offline_account("Jun")
    recorded = stub_launch(monkeypatch)
    bridge = LauncherBridge(launcher)
    bridge.playServer("van", "s1.example:25565")
    wait_until(lambda: "server_address" in recorded and not bridge.busy)
    assert (recorded["instance_id"], recorded["server_address"]) == ("van", "s1.example:25565")
    assert recorded["world_folder"] == ""


def test_card_shows_servers_with_their_icon_and_a_click_joins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    seed_servers(launcher, count=5)
    launcher.add_offline_account("Jun")
    recorded = stub_launch(monkeypatch)
    view, _bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    card = root_item.findChild(QObject, "continueCard")
    assert card is not None
    wait_until(lambda: len(collect_items(card, "continueServerRow")) == 3)
    empty = find_item(card, "continueServerEmpty")
    assert empty is not None and empty.property("visible") is False
    first = collect_items(card, "continueServerRow")[0]
    assert first.property("worldName") == "Server 0"
    wait_until(lambda: first.property("iconReady") is True)
    assert collect_items(card, "continueServerRow")[1].property("iconReady") is False
    last = collect_items(card, "continueServerRow")[-1]
    card_item = root_item.findChild(QQuickItem, "continueCard")
    assert card_item is not None
    bottom = last.mapToItem(card_item, 0.0, float(last.property("height"))).y()
    assert bottom <= card_item.height() - 18, "3 server phải nằm gọn trong ô"

    center = first.mapToScene(QPointF(first.property("width") / 2, first.property("height") / 2))
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center.toPoint()
    )
    QGuiApplication.processEvents()
    wait_until(lambda: "server_address" in recorded)
    assert (recorded["instance_id"], recorded["server_address"]) == ("van", "s0.example:25565")


def test_card_explains_itself_when_no_server_was_added(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    seed(launcher)
    view, _bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    card = root_item.findChild(QObject, "continueCard")
    assert card is not None
    assert collect_items(card, "continueServerRow") == []
    empty = find_item(card, "continueServerEmpty")
    assert empty is not None and empty.property("visible") is True
