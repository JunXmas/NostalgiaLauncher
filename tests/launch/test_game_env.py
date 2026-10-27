"""Game không được kế thừa LD_LIBRARY_PATH mà PyInstaller đặt cho launcher đóng gói.

Bản cài /opt/nostalgia chạy game với LD_LIBRARY_PATH=/opt/nostalgia/_internal (glib riêng
của launcher). Mọi công cụ hệ thống mà game/mod gọi (gdbus của lời nhạc Nos Client, xdg-open…)
nạp nhầm glib đó rồi chết "undefined symbol" — tính năng tắt im lặng.
"""

import os
import sys
from pathlib import Path

import pytest

from nostalgia.launch.command import LaunchCommand
from nostalgia.launch.game_process import start_game

DEADLINE = 10.0


def _echo_env(tmp_path: Path) -> LaunchCommand:
    script = tmp_path / "echo_env.py"
    script.write_text(
        "import os\n"
        "print(os.environ.get('LD_LIBRARY_PATH', '<unset>'))\n"
        "print(os.environ.get('DYLD_LIBRARY_PATH', '<unset>'))\n",
        encoding="utf-8",
    )
    # `main_class` là đường dẫn script, giống test_game_process.python_command.
    return LaunchCommand(
        java_binary=Path(sys.executable),
        jvm_arguments=(),
        main_class=str(script),
        game_arguments=(),
        game_dir=tmp_path / "game",
    )


@pytest.mark.skipif(sys.platform == "win32", reason="LD_LIBRARY_PATH chỉ có nghĩa trên Linux/macOS")
def test_game_does_not_inherit_the_bundled_library_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/nostalgia/_internal")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    monkeypatch.setenv("DYLD_LIBRARY_PATH", "/Applications/Nostalgia.app/lib")
    monkeypatch.delenv("DYLD_LIBRARY_PATH_ORIG", raising=False)
    lines: list[str] = []

    start_game(_echo_env(tmp_path), on_output=lines.append).wait(timeout=DEADLINE)

    assert lines == ["<unset>", "<unset>"]


@pytest.mark.skipif(sys.platform == "win32", reason="LD_LIBRARY_PATH chỉ có nghĩa trên Linux/macOS")
def test_game_gets_back_the_users_own_library_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # PyInstaller cất giá trị gốc của người dùng vào *_ORIG: game phải nhận lại đúng giá trị đó.
    monkeypatch.setenv("LD_LIBRARY_PATH", "/opt/nostalgia/_internal")
    monkeypatch.setenv("LD_LIBRARY_PATH_ORIG", "/home/user/lib")
    monkeypatch.delenv("DYLD_LIBRARY_PATH", raising=False)
    monkeypatch.delenv("DYLD_LIBRARY_PATH_ORIG", raising=False)
    lines: list[str] = []

    start_game(_echo_env(tmp_path), on_output=lines.append).wait(timeout=DEADLINE)

    assert lines == ["/home/user/lib", "<unset>"]
    assert os.environ["LD_LIBRARY_PATH"] == "/opt/nostalgia/_internal", "launcher không được đổi"
