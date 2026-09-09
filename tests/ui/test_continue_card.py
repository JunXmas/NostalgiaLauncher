"""Ô CHƠI TIẾP: hàng đúng thứ tự và chỉ quét đĩa khi bản chơi đổi / game tắt; `playWorld` đưa
thư mục thế giới xuống façade; QML vẽ đúng số nút khối (tối đa 4) và bấm nút mở đúng thế giới."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_home_layout import find_item
from test_qml import make_launcher

from nbt_fixture import write_world
from nostalgia.api import Instance, Launcher
from nostalgia.ui.app import build_view
from nostalgia.ui.bridge import LauncherBridge

pytestmark = pytest.mark.usefixtures("qt_app")

NOW_MS = 1_757_500_000_000
ROW_KEYS = {
    "instanceId",
    "instanceLabel",
    "worldFolder",
    "worldName",
    "lastPlayedAt",
    "lastPlayedText",
}


class FakeGame:
    def wait(self, _timeout: float | None = None) -> int:
        return 0


def seed(launcher: Launcher, *, worlds: int = 2) -> None:
    instance = launcher.create_instance(
        Instance(instance_id="van", version_id="1.20.1", display_name="Vanilla")
    )
    game_dir = launcher.instance_game_dir(instance)
    for number in range(worlds):
        write_world(game_dir, f"w{number}", f"Thế giới {number}", NOW_MS - number * 3_600_000)


def stub_launch(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    recorded: dict[str, Any] = {}

    def fake_launch(
        _self: Launcher, instance_id: str, _player_name: str, **kwargs: Any
    ) -> FakeGame:
        recorded.update(kwargs, instance_id=instance_id)
        return FakeGame()

    monkeypatch.setattr(Launcher, "launch_instance", fake_launch)
    monkeypatch.setattr(Launcher, "install_version", lambda *_args, **_kwargs: None)
    return recorded


def collect_items(node: QQuickItem, name: str) -> list[QQuickItem]:
    found = [node] if node.objectName() == name else []
    for child in node.childItems():
        found.extend(collect_items(child, name))
    return found


def test_rows_are_cached_and_refreshed_only_on_the_two_signals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    seed(launcher)
    scans: list[int] = []
    original = Launcher.list_recent_worlds

    def counted(self: Launcher, **kwargs: Any) -> Any:
        scans.append(1)
        return original(self, **kwargs)

    monkeypatch.setattr(Launcher, "list_recent_worlds", counted)
    bridge = LauncherBridge(launcher)
    rows = bridge.recentWorlds
    assert [row["worldName"] for row in rows] == ["Thế giới 0", "Thế giới 1"]
    assert set(rows[0]) == ROW_KEYS
    assert (rows[0]["instanceLabel"], rows[0]["worldFolder"]) == ("Vanilla", "w0")
    again = [bridge.recentWorlds for _ in range(10)]
    assert scans == [1] and len(again) == 10, "đọc lại property không được quét đĩa lại"
    bridge.instancesChanged.emit()
    after_change = bridge.recentWorlds
    bridge.gameStopped.emit(0)
    after_stop = bridge.recentWorlds
    assert len(scans) == 3 and len(after_change) == len(after_stop) == 2


def test_play_world_hands_the_folder_to_the_facade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    seed(launcher)
    launcher.add_offline_account("Jun")
    recorded = stub_launch(monkeypatch)
    bridge = LauncherBridge(launcher)
    bridge.playWorld("van", "w1")
    wait_until(lambda: "world_folder" in recorded and not bridge.busy)
    assert (recorded["instance_id"], recorded["world_folder"]) == ("van", "w1")


def test_card_shows_at_most_four_block_buttons_and_a_click_opens_that_world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    seed(launcher, worlds=6)
    launcher.add_offline_account("Jun")
    recorded = stub_launch(monkeypatch)
    view, _bridge = build_view(launcher)
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    card = root_item.findChild(QObject, "continueCard")
    assert card is not None
    wait_until(lambda: len(collect_items(card, "continueRow")) == 4)
    empty = find_item(card, "continueEmpty")
    assert empty is not None and empty.property("visible") is False
    first = collect_items(card, "continueRow")[0]
    assert first.property("worldName") == "Thế giới 0"
    assert first.property("height") * 4 + 15 <= card.property("height") - 60, "4 nút phải nằm gọn"

    center = first.mapToScene(QPointF(first.property("width") / 2, first.property("height") / 2))
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center.toPoint()
    )
    QGuiApplication.processEvents()
    wait_until(lambda: "world_folder" in recorded)
    assert (recorded["instance_id"], recorded["world_folder"]) == ("van", "w0")


def test_card_explains_itself_when_there_is_nothing_to_continue(tmp_path: Path) -> None:
    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    card = root_item.findChild(QObject, "continueCard")
    assert card is not None
    assert collect_items(card, "continueRow") == []
    empty = find_item(card, "continueEmpty")
    assert empty is not None and empty.property("visible") is True
