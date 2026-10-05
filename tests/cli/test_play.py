"""Lệnh `play`: từ chối đúng chỗ, và dựng đúng lệnh cho bản chơi."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli_fixture import (
    INSTANCE_ID,
    install_and_create_instance,
    make_paths,
    roots,
)
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.cli.main import main
from nostalgia.net.http import HttpClient


def test_play_refuses_without_an_account(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "KhongCo"]) == 1
    assert "account list" in capsys.readouterr().err


def test_play_refuses_when_the_version_is_not_installed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bản chơi có thể trỏ vào phiên bản chưa tải — nói đúng lệnh cần chạy."""
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    main([*roots(tmp_path), "instance", "create", "moi", "--version", "1.20.1"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", "moi", "--account", "Jun"]) == 1
    assert "nostalgia install 1.20.1" in capsys.readouterr().err


def test_playing_a_version_id_by_mistake_says_how_to_make_an_instance(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Người quen mốc M1 hay gõ thẳng mã phiên bản; đừng bắt họ đi tìm trong trợ giúp."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", VERSION_ID, "--account", "Jun"]) == 1

    reported = capsys.readouterr().err
    assert "không phải bản chơi" in reported
    assert f"instance create {VERSION_ID} --version {VERSION_ID}" in reported


def test_play_prints_the_command_without_starting_anything(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--print-command` là cách gỡ lỗi chính khi game không chịu chạy."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Jun", "--print-command"]) == 0

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
    install_and_create_instance(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    make_paths(tmp_path).version_jar(VERSION_ID).unlink()
    capsys.readouterr()

    assert main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Jun"]) == 1
    assert "--repair" in capsys.readouterr().err


def test_the_command_carries_the_memory_flag_the_user_asked_for(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_and_create_instance(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    main(
        [
            *roots(tmp_path),
            "play",
            INSTANCE_ID,
            "--account",
            "Jun",
            "--max-memory",
            "3072",
            "--print-command",
        ]
    )

    assert "-Xmx3072M" in capsys.readouterr().out


def test_each_instance_plays_in_its_own_directory(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Trộn chung thư mục chơi là bản mới ăn thế giới của bản cũ."""
    install_and_create_instance(server, server_state, http_client, tmp_path)
    main([*roots(tmp_path), "instance", "create", "ban-hai", "--version", VERSION_ID])
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    capsys.readouterr()

    main([*roots(tmp_path), "play", INSTANCE_ID, "--account", "Jun", "--print-command"])
    first = capsys.readouterr().out
    main([*roots(tmp_path), "play", "ban-hai", "--account", "Jun", "--print-command"])
    second = capsys.readouterr().out

    assert f"instances/{INSTANCE_ID}" in first
    assert "instances/ban-hai" in second
    assert first != second, "hai bản chơi phải chạy ở hai thư mục khác nhau"
