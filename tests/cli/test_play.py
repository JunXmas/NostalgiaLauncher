"""Lệnh `play`: từ chối đúng chỗ, và chạy thật khi mọi thứ đã đủ."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli_fixture import fake_java_binary, install_fake_version, make_paths, roots
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.cli.main import main
from nostalgia.net.http import HttpClient


def test_play_refuses_without_an_account(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "play", VERSION_ID, "--account", "KhongCo"]) == 1
    assert "account list" in capsys.readouterr().err


def test_play_refuses_when_the_version_is_not_installed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", "1.20.1", "--account", "Jun"]) == 1
    assert "nostalgia install 1.20.1" in capsys.readouterr().err


def test_play_prints_the_command_without_starting_anything(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--print-command` là cách gỡ lỗi chính khi game không chịu chạy."""
    install_fake_version(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", VERSION_ID, "--account", "Jun", "--print-command"]) == 0

    printed = capsys.readouterr().out
    assert "bin/java" in printed
    assert "--username Jun" in printed
    assert "${" not in printed, "lệnh còn biến chưa thay là lệnh hỏng"
    assert "net.minecraft.client.main.Main" in printed


def test_play_refuses_a_broken_install_and_names_the_repair_command(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_fake_version(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    make_paths(tmp_path).version_jar(VERSION_ID).unlink()
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", VERSION_ID, "--account", "Jun"]) == 1
    assert "--repair" in capsys.readouterr().err


def test_the_command_carries_the_memory_flag_the_user_asked_for(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_fake_version(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    main(
        [
            *roots(tmp_path),
            "play",
            VERSION_ID,
            "--account",
            "Jun",
            "--max-memory",
            "3072",
            "--print-command",
        ]
    )

    assert "-Xmx3072M" in capsys.readouterr().out


def test_each_version_gets_its_own_game_directory_by_default(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Trộn chung thư mục chạy là bản mới ăn thế giới của bản cũ."""
    install_fake_version(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    main([*roots(tmp_path), "play", VERSION_ID, "--account", "Jun", "--print-command"])

    assert f"game/{VERSION_ID}" in capsys.readouterr().out


def test_play_actually_starts_the_binary_and_returns_its_exit_code(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Đi trọn đường: cài → tạo tài khoản → chạy. "java" ở đây là một script shell thật."""
    install_fake_version(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", VERSION_ID, "--account", "Jun"]) == 0

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
    install_fake_version(server, server_state, http_client, tmp_path)
    java_binary = fake_java_binary(tmp_path)
    java_binary.write_text("#!/bin/sh\nexit 42\n", encoding="utf-8")
    java_binary.chmod(0o755)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", VERSION_ID, "--account", "Jun"]) == 42


def test_quiet_mode_still_drains_the_pipe(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Không đọc ống thì game nghẽn khi bộ đệm đầy — im lặng không có nghĩa là bỏ đọc."""
    install_fake_version(server, server_state, http_client, tmp_path)
    java_binary = fake_java_binary(tmp_path)
    java_binary.write_text(
        "#!/bin/sh\nfor i in $(seq 1 4000); do echo dong-$i; done\nexit 0\n", encoding="utf-8"
    )
    java_binary.chmod(0o755)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "--quiet", "play", VERSION_ID, "--account", "Jun"]) == 0
    assert "dong-4000" not in capsys.readouterr().out
