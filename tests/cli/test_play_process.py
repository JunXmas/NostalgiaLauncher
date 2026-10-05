"""Lệnh `play` chạy tiến trình thật: mã thoát, log, và chế độ im lặng."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli_fixture import (
    INSTANCE_ID,
    fake_java_binary,
    install_and_create_instance,
    install_fake_version,
    roots,
)
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.cli.main import main
from nostalgia.net.http import HttpClient


def test_play_actually_starts_the_binary_and_returns_its_exit_code(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Đi trọn đường: cài → tạo tài khoản → chạy. "java" ở đây là một script shell thật."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Jun"]) == 0

    captured = capsys.readouterr()
    assert "khởi động" in captured.out
    assert "fake java" in captured.out, "output của game phải chảy ra màn hình"


def test_the_exit_code_of_the_game_reaches_the_shell(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Script bao bọc bên ngoài dựa vào mã thoát; nuốt nó là làm hỏng mọi tự động hoá."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    java_binary = fake_java_binary(tmp_path)
    java_binary.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
    java_binary.chmod(0o755)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Jun"]) == 42


def test_quiet_mode_still_drains_the_pipe(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Không đọc ống thì game nghẽn khi bộ đệm đầy — im lặng không có nghĩa là bỏ đọc."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    java_binary = fake_java_binary(tmp_path)
    java_binary.write_text(
        "#!/bin/sh\nfor i in $(seq 1 4000); do echo dong-$i; done\nexit 0\n", encoding="utf-8"
    )
    java_binary.chmod(0o755)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "--quiet", "play", INSTANCE_ID, "--account", "Jun"]) == 0
    assert "dong-4000" not in capsys.readouterr().out


def test_the_instance_settings_apply_without_repeating_them_every_time(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Đặt một lần lúc tạo bản chơi là đủ — đó chính là điểm của việc có bản chơi."""
    install_fake_version(server, server_state, http_client, tmp_path)
    main(
        [
            *roots(tmp_path),
            "instance",
            "create",
            "nang",
            "--version",
            VERSION_ID,
            "--max-memory",
            "6144",
            "--width",
            "1600",
            "--height",
            "900",
        ]
    )
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    main([*roots(tmp_path), "play", "nang", "--account", "Jun", "--print-command"])

    printed = capsys.readouterr().out
    assert "-Xmx6144M" in printed
    assert "--width 1600" in printed
    assert "--height 900" in printed


def test_a_command_line_flag_beats_the_instance_setting(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Người dùng gõ cờ cho ĐÚNG lần chạy này; nó phải thắng cấu hình đã lưu."""
    install_fake_version(server, server_state, http_client, tmp_path)
    main(
        [
            *roots(tmp_path),
            "instance",
            "create",
            "nang",
            "--version",
            VERSION_ID,
            "--max-memory",
            "6144",
        ]
    )
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    main(
        [
            *roots(tmp_path),
            "play",
            "nang",
            "--account",
            "Jun",
            "--max-memory",
            "1024",
            "--print-command",
        ]
    )

    printed = capsys.readouterr().out
    assert "-Xmx1024M" in printed
    assert "-Xmx6144M" not in printed
