"""Discord Rich Presence: khung IPC đúng định dạng, bắt tay rồi SET_ACTIVITY qua socket giả,
không có Discord thì im lặng, và cầu nối bật/tắt theo game chạy."""

from __future__ import annotations

import socket
import threading
from collections.abc import Callable
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
    read_frame,
)
from nostalgia.ui.presence_bridge import PresenceBridge

pytestmark = pytest.mark.usefixtures("qt_app")


class FakeDiscord:
    """Một Discord giả: nghe trên `discord-ipc-0` trong thư mục tạm, ghi lại mọi khung nhận.
    `activity_evt` điều khiển phản hồi cho SET_ACTIVITY — mặc định `None` (thành công), đặt
    `"ERROR"` để mô phỏng Application ID sai."""

    def __init__(self, runtime_dir: Path, activity_evt: str | None = None) -> None:
        self.path = runtime_dir / "discord-ipc-0"
        self.frames: list[tuple[int, dict[str, object]]] = []
        self._activity_evt = activity_evt
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
                    connection.sendall(
                        encode_frame(OP_FRAME, {"cmd": "SET_ACTIVITY", "evt": self._activity_evt})
                    )
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
    assert str(candidate_socket_paths({}, "win32")[0]) == r"\\.\pipe\discord-ipc-0"


def test_socket_paths_fall_back_to_run_user_uid_without_xdg_runtime_dir() -> None:
    paths = candidate_socket_paths({}, "linux")
    assert any(str(path).startswith("/run/user/") for path in paths), (
        "thiếu XDG_RUNTIME_DIR (vd chạy từ systemd service) vẫn phải thử /run/user/<uid>"
    )


def test_read_frame_reassembles_a_frame_split_across_many_recv_calls() -> None:
    frame = encode_frame(OP_FRAME, {"cmd": "SET_ACTIVITY", "evt": None})
    chunks = [frame[index : index + 3] for index in range(0, len(frame), 3)]

    def fragmented_recv(_size: int) -> bytes:
        return chunks.pop(0) if chunks else b""

    assert read_frame(fragmented_recv) == (OP_FRAME, {"cmd": "SET_ACTIVITY", "evt": None})


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


def test_set_activity_reports_failure_when_discord_answers_with_error(tmp_path: Path) -> None:
    fake = FakeDiscord(tmp_path, activity_evt="ERROR")
    presence = DiscordPresence("123456789", environ={"XDG_RUNTIME_DIR": str(tmp_path)})
    assert presence.connect() is True
    assert presence.set_activity("x", "y", 0) is False, (
        "Discord trả evt == ERROR (vd Application ID sai) không được báo thành công"
    )
    presence.close()
    fake.close()


def test_without_discord_everything_stays_quiet(tmp_path: Path) -> None:
    presence = DiscordPresence("123", environ={"XDG_RUNTIME_DIR": str(tmp_path)})
    assert presence.connect() is False and presence.connected is False
    assert presence.set_activity("x", "y", 0) is False
    presence.close()
    assert DiscordPresence("   ", environ={"XDG_RUNTIME_DIR": str(tmp_path)}).connect() is False


def _make_bridge(
    tmp_path: Path,
    bridge: LauncherBridge,
    *,
    enabled: Callable[[], bool] = lambda: True,
    retry_seconds: float = 3600.0,
) -> PresenceBridge:
    """Hẹn giờ thử lại mặc định đặt rất xa: test nào muốn đo nhịp thử lại thì tự rút ngắn,
    còn lại không phải chịu một luồng nền bật lên giữa chừng làm kết quả chập chờn."""
    return PresenceBridge(
        bridge,
        is_enabled=enabled,
        instance_label=lambda _instance_id: "Sinh tồn",
        client_id="987",
        make_presence=lambda client_id: DiscordPresence(
            client_id, environ={"XDG_RUNTIME_DIR": str(tmp_path)}, pid=1
        ),
        retry_seconds=retry_seconds,
    )


def _latest_activity(fake: FakeDiscord) -> dict[str, object] | None:
    frames = [frame for frame in fake.frames if frame[0] == OP_FRAME]
    if not frames:
        return None
    arguments = frames[-1][1]["args"]
    assert isinstance(arguments, dict)
    activity = arguments["activity"]
    assert isinstance(activity, dict)
    return activity


def test_bridge_shows_launcher_presence_before_any_game_starts(tmp_path: Path) -> None:
    """Mở launcher là đã hiện trên Discord — không bắt người chơi khởi động game mới thấy gì."""
    fake = FakeDiscord(tmp_path)
    presence_bridge = _make_bridge(tmp_path, LauncherBridge(make_launcher(tmp_path)))

    wait_until(lambda: presence_bridge.connected is True)
    assert _latest_activity(fake) is not None
    activity = _latest_activity(fake)
    assert activity is not None and activity["details"] == "Đang ở launcher"
    presence_bridge.shutdown()
    fake.close()


def test_bridge_retries_when_discord_opens_after_the_launcher(tmp_path: Path) -> None:
    """Người chơi hay mở launcher trước rồi mới mở Discord. Thất bại lần đầu mà im mãi thì
    với họ tính năng coi như không tồn tại."""
    presence_bridge = _make_bridge(
        tmp_path, LauncherBridge(make_launcher(tmp_path)), retry_seconds=0.05
    )
    wait_until(lambda: presence_bridge.statusText == "Không thấy Discord đang chạy")

    fake = FakeDiscord(tmp_path)  # Discord mở SAU
    wait_until(lambda: presence_bridge.connected is True, seconds=5)
    presence_bridge.shutdown()
    fake.close()


def test_bridge_shows_presence_while_the_game_runs(tmp_path: Path) -> None:
    fake = FakeDiscord(tmp_path)
    launcher = make_launcher(tmp_path)
    bridge = LauncherBridge(launcher)
    enabled = {"on": True}
    presence_bridge = _make_bridge(
        tmp_path, bridge, enabled=lambda: enabled["on"], retry_seconds=0.05
    )
    wait_until(lambda: presence_bridge.connected is True)

    bridge.gameStarted.emit("sinh-ton")
    wait_until(lambda: (_latest_activity(fake) or {}).get("details") == "Đang chơi Sinh tồn")
    assert presence_bridge.statusText == "Đang hiện trên Discord"
    activity = _latest_activity(fake)
    assert activity is not None and activity["state"] == "Nostalgia Launcher"

    bridge.gameStopped.emit(0)
    wait_until(lambda: (_latest_activity(fake) or {}).get("details") == "Đang ở launcher")
    assert presence_bridge.connected is True, "thoát game không phải là thoát launcher"

    enabled["on"] = False
    wait_until(lambda: presence_bridge.statusText == "Đã xoá trạng thái", seconds=5)
    wait_until(lambda: any(frame[0] == OP_CLOSE for frame in fake.frames), seconds=3)
    assert presence_bridge.connected is False, "tắt trong CÀI ĐẶT thì gỡ presence khỏi Discord"
    presence_bridge.shutdown()
    fake.close()


def test_bridge_shows_shared_room_state_while_playing_together(tmp_path: Path) -> None:
    fake = FakeDiscord(tmp_path)
    launcher = make_launcher(tmp_path)
    bridge = LauncherBridge(launcher)
    presence_bridge = _make_bridge(tmp_path, bridge)

    bridge.gameStarted.emit("sinh-ton")
    wait_until(lambda: presence_bridge.connected is True)

    presence_bridge.setRoomState("hosting", 2)
    wait_until(lambda: (_latest_activity(fake) or {}).get("state") == "Đang chơi chung với 2 người")

    presence_bridge.setRoomState("idle", 0)
    wait_until(lambda: (_latest_activity(fake) or {}).get("state") == "Nostalgia Launcher")

    presence_bridge.shutdown()
    fake.close()
