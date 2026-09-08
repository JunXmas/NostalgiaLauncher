"""Thông báo sự kiện khởi chạy: toast lên đúng lúc, chuông chỉ kêu khi bật, WAV tự sinh hợp lệ,
trình phát chọn theo hệ điều hành và không bao giờ chặn."""

from __future__ import annotations

import io
import wave
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from PySide6.QtCore import QObject
from test_bridges import wait_until
from test_qml import make_launcher

from nostalgia.ui.app import build_view
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.notifier import Notifier
from nostalgia.ui.sound import SoundPlayer, render_chime, resolve_player_command

pytestmark = pytest.mark.usefixtures("qt_app")


def test_rendered_chime_is_a_valid_short_wav() -> None:
    with wave.open(io.BytesIO(render_chime((660.0, 880.0))), "rb") as reader:
        assert (reader.getnchannels(), reader.getsampwidth()) == (1, 2)
        seconds = reader.getnframes() / reader.getframerate()
    assert 0.2 < seconds < 0.4, "hai nốt ngắn, không phải một bản nhạc"


def test_player_command_follows_the_platform() -> None:
    assert resolve_player_command(
        "linux", lambda name: "/usr/bin/paplay" if name == "paplay" else None
    ) == ("paplay",)
    assert resolve_player_command(
        "linux", lambda name: "/usr/bin/aplay" if name == "aplay" else None
    ) == ("aplay",)
    assert resolve_player_command("linux", lambda _name: None) == ()
    assert resolve_player_command("darwin", lambda _name: "/usr/bin/afplay") == ("afplay",)
    assert resolve_player_command("win32", lambda _name: None) == ()


def test_player_writes_the_wav_once_and_spawns_without_waiting(tmp_path: Path) -> None:
    spawned: list[list[str]] = []
    player = SoundPlayer(
        tmp_path / "sounds",
        platform_name="linux",
        spawn=lambda argv: spawned.append(list(argv)),
        which=lambda name: "/usr/bin/paplay" if name == "paplay" else None,
    )
    assert player.play("started") is True
    assert player.play("started") is True
    assert spawned[0][0] == "paplay" and spawned[0][1].endswith("chime-started.wav")
    assert len(list((tmp_path / "sounds").iterdir())) == 1, "cùng sự kiện dùng lại một file"

    silent = SoundPlayer(
        tmp_path / "s2", platform_name="linux", spawn=spawned.append, which=lambda _n: None
    )
    assert silent.play("crashed") is False, "không có trình phát thì im lặng, không ném lỗi"


def test_notifier_announces_launch_events_and_respects_the_sound_switch(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    bridge = LauncherBridge(launcher)
    played: list[str] = []
    player = SoundPlayer(
        tmp_path / "sounds",
        platform_name="linux",
        spawn=lambda argv: played.append(argv[-1]),
        which=lambda _n: "/usr/bin/paplay",
    )
    enabled = {"sound": True}
    notifier = Notifier(
        bridge,
        player=player,
        sound_enabled=lambda: enabled["sound"],
        instance_label=lambda instance_id: {"sinh-ton": "Sinh tồn"}.get(instance_id, instance_id),
    )
    seen: list[tuple[str, str, str]] = []
    notifier.notified.connect(
        lambda event_kind, title, detail: seen.append((event_kind, title, detail))
    )

    bridge.gameStarted.emit("sinh-ton")
    bridge.gameStopped.emit(0)
    bridge.gameStopped.emit(1)
    bridge.versionInstalled.emit("1.20.1")
    wait_until(lambda: len(seen) == 4)
    assert [event[0] for event in seen] == ["started", "stopped", "crashed", "installed"]
    assert seen[0][2] == "Sinh tồn" and "1" in seen[2][2] and "1.20.1" in seen[3][2]
    assert [Path(path).name for path in played] == [
        "chime-started.wav",
        "chime-stopped.wav",
        "chime-crashed.wav",
        "chime-installed.wav",
    ]

    enabled["sound"] = False
    bridge.gameStarted.emit("sinh-ton")
    wait_until(lambda: len(seen) == 5)
    assert len(played) == 4, "tắt âm thanh thì toast vẫn lên nhưng chuông im"


def test_toast_shows_the_event_on_screen(tmp_path: Path) -> None:
    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    toast = root_item.findChild(QObject, "notificationToast")
    title = root_item.findChild(QObject, "notificationTitle")
    assert toast is not None and title is not None
    assert toast.property("shown") is False

    notifier = view.rootContext().contextProperty("notifier")
    notifier.announce("started", "Game đã khởi động", "Sinh tồn")
    wait_until(lambda: toast.property("shown") is True)
    assert title.property("text") == "Game đã khởi động"
