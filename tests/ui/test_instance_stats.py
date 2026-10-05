"""Thống kê chơi lên tới QML: mỗi hàng bản chơi có giờ chơi, số lần chạy, thế giới, mod; hàng
được giữ trong RAM và chỉ dựng lại khi danh sách đổi."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from test_qml import make_launcher

from nostalgia.api import Instance, Launcher
from nostalgia.instance.stats import InstanceStats
from nostalgia.ui.bridge import LauncherBridge

pytestmark = pytest.mark.usefixtures("qt_app")


def test_rows_carry_stats_and_are_rebuilt_only_when_told(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(tmp_path)
    launcher.create_instance(Instance(instance_id="sinh-ton", version_id="1.20.1"))
    game_dir = launcher.paths.instance_dir("sinh-ton")
    (game_dir / "saves" / "Nhà").mkdir(parents=True)
    (game_dir / "saves" / "Nhà" / "level.dat").write_bytes(b"\x00")
    (game_dir / "mods").mkdir()
    (game_dir / "mods" / "sodium.jar").write_bytes(b"PK")
    (game_dir / "mods" / "iris.jar").write_bytes(b"PK")

    scans: list[str] = []
    original = Launcher.describe_instance_stats

    def counted(self: Launcher, instance_id: str) -> InstanceStats:
        scans.append(instance_id)
        return original(self, instance_id)

    monkeypatch.setattr(Launcher, "describe_instance_stats", counted)
    bridge = LauncherBridge(launcher)

    [row] = bridge.instances
    assert (row["playtimeText"], row["launchCount"], row["worldCount"], row["modCount"]) == (
        "chưa chơi",
        0,
        1,
        2,
    )
    for _ in range(10):
        assert bridge.instances[0]["modCount"] == 2
    assert scans == ["sinh-ton"], "đọc lại property không được quét đĩa lại"

    launcher.record_play_session("sinh-ton", started_at=0.0, ended_at=95 * 60.0)
    bridge.instancesChanged.emit()
    [row] = bridge.instances
    assert (row["playtimeText"], row["launchCount"], row["lastPlayedAt"]) == (
        "1 giờ 35 phút",
        1,
        95 * 60,
    )
    assert scans == ["sinh-ton", "sinh-ton"]
