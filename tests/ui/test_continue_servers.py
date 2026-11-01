"""Server đã thêm trong game (`recentServers`): hàng đúng khoá và chỉ quét lại khi bản chơi
đổi / game tắt; `playServer` đưa địa chỉ xuống façade."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from test_bridges import wait_until
from test_continue_card import seed, stub_launch
from test_qml import make_launcher

from nbt_fixture import tiny_png, write_servers
from nostalgia.api import Launcher
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
