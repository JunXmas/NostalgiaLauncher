"""Thông báo sự kiện khởi chạy: toast lên đúng lúc, chuông chỉ kêu khi bật, WAV tự sinh hợp lệ,
trình phát chọn theo hệ điều hành và không bao giờ chặn; blip giao diện có công tắc riêng, nối
đúng vào thanh bên / nút / hộp thoại, và NOSTALGIA_SILENT=1 tắt hẳn."""

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
from nostalgia.ui.sound import (
    UI_SOUNDS,
    SoundPlayer,
    render_chime,
    render_sound,
    resolve_player_command,
)

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
        environment={},
    )
    assert player.play("started") is True
    assert player.play("started") is True
    assert spawned[0][0] == "paplay" and "/sound-started-" in spawned[0][1]
    assert len(list((tmp_path / "sounds").iterdir())) == 1, "cùng sự kiện dùng lại một file"

    # Đổi công thức tổng hợp → băm trong tên đổi → bản cũ cùng tên tiếng bị dọn, không phát nhầm.
    stale = tmp_path / "sounds" / "sound-select-00000000.wav"
    stale.write_bytes(b"cu")
    assert player.play("select") is True
    assert not stale.exists() and len(list((tmp_path / "sounds").iterdir())) == 2

    silent = SoundPlayer(
        tmp_path / "s2",
        platform_name="linux",
        spawn=spawned.append,
        which=lambda _n: None,
        environment={},
    )
    assert silent.play("crashed") is False, "không có trình phát thì im lặng, không ném lỗi"

    muted = SoundPlayer(
        tmp_path / "s3",
        platform_name="linux",
        spawn=spawned.append,
        which=lambda _n: "/usr/bin/paplay",
        environment={"NOSTALGIA_SILENT": "1"},
    )
    assert muted.play("select") is False and not (tmp_path / "s3").exists(), (
        "NOSTALGIA_SILENT=1: không sinh file, không gọi trình phát"
    )


def test_notifier_announces_launch_events_and_respects_the_sound_switch(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    bridge = LauncherBridge(launcher)
    played: list[str] = []
    player = SoundPlayer(
        tmp_path / "sounds",
        platform_name="linux",
        spawn=lambda argv: played.append(argv[-1]),
        which=lambda _n: "/usr/bin/paplay",
        environment={},
    )
    enabled = {"sound": True, "ui": True}
    notifier = Notifier(
        bridge,
        player=player,
        sound_enabled=lambda: enabled["sound"],
        ui_sound_enabled=lambda: enabled["ui"],
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
    assert [Path(path).name.rsplit("-", 1)[0] for path in played] == [
        "sound-started",
        "sound-stopped",
        "sound-crashed",
        "sound-installed",
    ]

    enabled["sound"] = False
    bridge.gameStarted.emit("sinh-ton")
    wait_until(lambda: len(seen) == 5)
    assert len(played) == 4, "tắt âm thanh thì toast vẫn lên nhưng chuông im"

    # Blip giao diện đi theo công tắc RIÊNG: chuông tắt mà blip vẫn kêu, và ngược lại.
    notifier.playUi("select")
    assert Path(played[-1]).name.startswith("sound-select-")
    enabled["ui"] = False
    notifier.playUi("nav")
    assert len(played) == 5


def test_ui_sounds_are_short_soft_and_stable() -> None:
    """Tiếng dashboard: dưới 0,7 s kể cả vang, nhỏ hơn chuông, tắt hẳn ở cuối, và cùng tên luôn
    ra cùng byte (ồn trắng gieo hạt cố định → cache và test ổn định)."""
    for sound_name in UI_SOUNDS:
        assert render_sound(sound_name) == render_sound(sound_name), sound_name
        with wave.open(io.BytesIO(render_sound(sound_name)), "rb") as reader:
            assert (reader.getnchannels(), reader.getsampwidth()) == (1, 2), sound_name
            duration = reader.getnframes() / reader.getframerate()
            samples = reader.readframes(reader.getnframes())
        assert 0.05 <= duration <= 0.7, f"{sound_name}: tiếng giao diện phải ngắn"
        peak = max(
            abs(int.from_bytes(samples[i : i + 2], "little", signed=True))
            for i in range(0, len(samples), 2)
        )
        assert 0.2 * 32767 < peak <= 0.3 * 32767, f"{sound_name}: nhỏ hơn chuông nhưng nghe được"
        assert samples[-2:] == b"\x00\x00", f"{sound_name}: phải tắt hẳn ở cuối, không 'cạch'"


def test_ui_taps_reach_the_notifier(tmp_path: Path) -> None:
    """Dây nối QML → notifier.playUi: mở hộp Tạo bản chơi = open, chọn loader = nav, bấm ra
    ngoài để đóng = back. Loa thật im vì conftest đặt NOSTALGIA_SILENT=1."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtTest import QTest

    view, _bridge = build_view(make_launcher(tmp_path))
    view.show()
    root_item = view.rootObject()
    assert root_item is not None
    notifier = view.rootContext().contextProperty("notifier")
    played: list[str] = []
    notifier.uiSoundPlayed.connect(played.append)
    sidebar = root_item.findChild(QObject, "sidebar")
    assert sidebar is not None
    sidebar.setProperty("currentIndex", 1)
    wait_until(lambda: root_item.findChild(QObject, "createDialog") is not None)
    dialog = root_item.findChild(QObject, "createDialog")
    assert dialog is not None
    dialog.openDialog()
    QGuiApplication.processEvents()
    loader_row = root_item.findChild(QObject, "loaderRow")
    assert loader_row is not None
    fabric_button = loader_row.childItems()[1]
    center = fabric_button.mapToScene(
        QPointF(fabric_button.property("width") / 2, fabric_button.property("height") / 2)
    )
    QTest.mouseClick(
        view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, center.toPoint()
    )
    QTest.mouseClick(
        view,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPointF(view.width() - 5, 5).toPoint(),
    )
    QGuiApplication.processEvents()
    assert played == ["open", "nav", "back"]


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
