"""Discord Rich Presence: khung IPC đúng định dạng, bắt tay rồi SET_ACTIVITY qua socket giả,
không có Discord thì im lặng, và cầu nối bật/tắt theo game chạy."""

from __future__ import annotations

import socket
import threading
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

from test_bridges import wait_until
from test_qml import make_launcher

from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.discord_presence import (
    OP_CLOSE,
    OP_FRAME,
    OP_HANDSHAKE,
    DiscordPresence,
    candidate_socket_paths,
    decode_frame,
    encode_frame,
)
from nostalgia.ui.presence_bridge import PresenceBridge

pytestmark = pytest.mark.usefixtures("qt_app")


class FakeDiscord:
    """Một Discord giả: nghe trên `discord-ipc-0` trong thư mục tạm, ghi lại mọi khung nhận."""

    def __init__(self, runtime_dir: Path) -> None:
        self.path = runtime_dir / "discord-ipc-0"
        self.frames: list[tuple[int, dict[str, object]]] = []
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(str(self.path))
        self._server.listen(1)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        connection, _ = self._server.accept()
        with connection:
            while True:
                try:
                    chunk = connection.recv(65536)
                except OSError:
                    return
                if not chunk:
                    return
                frame = decode_frame(chunk)
                if frame is None:
                    continue
                self.frames.append(frame)
                if frame[0] == OP_HANDSHAKE:
                    connection.sendall(encode_frame(OP_FRAME, {"cmd": "DISPATCH", "evt": "READY"}))
                elif frame[0] == OP_FRAME:
                    connection.sendall(encode_frame(OP_FRAME, {"cmd": "SET_ACTIVITY", "evt": None}))
                elif frame[0] == OP_CLOSE:
                    return

    def close(self) -> None:
        self._server.close()


def test_frames_round_trip_and_socket_paths_follow_the_platform(tmp_path: Path) -> None:
    frame = encode_frame(OP_FRAME, {"cmd": "SET_ACTIVITY"})
    assert frame[:8] == b"\x01\x00\x00\x00\x16\x00\x00\x00"  # opcode 1, 22 byte JSON
    assert decode_frame(frame) == (OP_FRAME, {"cmd": "SET_ACTIVITY"})
    assert decode_frame(frame[:-1]) is None, "khung thiếu byte thì chờ tiếp, không ném"
    paths = candidate_socket_paths({"XDG_RUNTIME_DIR": str(tmp_path)}, "linux")
    assert (
        paths[0] == tmp_path / "discord-ipc-0"
        and (tmp_path / "snap.discord" / "discord-ipc-0") in paths
    )
    assert Path("/tmp/discord-ipc-3") in paths
    assert str(candidate_socket_paths({}, "win32")[0]).endswith("discord-ipc-0")


def test_handshake_then_activity_reaches_the_fake_discord(tmp_path: Path) -> None:
    fake = FakeDiscord(tmp_path)
    presence = DiscordPresence("123456789", environ={"XDG_RUNTIME_DIR": str(tmp_path)}, pid=4242)
    assert presence.connect() is True
    assert presence.set_activity("Đang chơi Sinh tồn", "Nostalgia Launcher", 1_700_000_000) is True
    presence.close()
    wait_until(lambda: len(fake.frames) == 3, seconds=3)
    fake.close()

    handshake, activity, closing = fake.frames
    assert handshake == (OP_HANDSHAKE, {"v": 1, "client_id": "123456789"})
    assert activity[0] == OP_FRAME and activity[1]["cmd"] == "SET_ACTIVITY"
    arguments = activity[1]["args"]
    assert isinstance(arguments, dict) and arguments["pid"] == 4242
    assert arguments["activity"] == {
        "details": "Đang chơi Sinh tồn",
        "state": "Nostalgia Launcher",
        "timestamps": {"start": 1_700_000_000},
    }
    assert closing[0] == OP_CLOSE


def test_without_discord_everything_stays_quiet(tmp_path: Path) -> None:
    presence = DiscordPresence("123", environ={"XDG_RUNTIME_DIR": str(tmp_path)})
    assert presence.connect() is False and presence.connected is False
    assert presence.set_activity("x", "y", 0) is False
    presence.close()
    assert DiscordPresence("   ", environ={"XDG_RUNTIME_DIR": str(tmp_path)}).connect() is False


def test_bridge_shows_presence_while_the_game_runs(tmp_path: Path) -> None:
    fake = FakeDiscord(tmp_path)
    launcher = make_launcher(tmp_path)
    bridge = LauncherBridge(launcher)
    settings = {"enabled": True, "client_id": "987"}
    presence_bridge = PresenceBridge(
        bridge,
        read_settings=lambda: (settings["enabled"], settings["client_id"]),
        instance_label=lambda _instance_id: "Sinh tồn",
        make_presence=lambda client_id: DiscordPresence(
            client_id, environ={"XDG_RUNTIME_DIR": str(tmp_path)}, pid=1
        ),
    )
    assert presence_bridge.connected is False

    bridge.gameStarted.emit("sinh-ton")
    wait_until(lambda: presence_bridge.connected is True)
    assert presence_bridge.statusText == "Đang hiện trên Discord"
    activity = next(frame for frame in fake.frames if frame[0] == OP_FRAME)
    arguments = activity[1]["args"]
    assert isinstance(arguments, dict)
    assert arguments["activity"]["details"] == "Đang chơi Sinh tồn"

    bridge.gameStopped.emit(0)
    wait_until(lambda: presence_bridge.connected is False)
    wait_until(lambda: any(frame[0] == OP_CLOSE for frame in fake.frames), seconds=3)
    fake.close()

    settings["enabled"] = False
    bridge.gameStarted.emit("sinh-ton")
    wait_until(lambda: presence_bridge.statusText == "Đã xoá trạng thái")
    assert presence_bridge.connected is False, "tắt trong CÀI ĐẶT thì không chạm Discord"
