"""Lệnh `account`, `version --installed` và `doctor`: mọi lối, kể cả lối hỏng."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli_fixture import install_fake_version, make_paths, roots
from fake_mojang import VERSION_ID
from local_https_server import LocalHttpsServer, ServerState
from nostalgia.account.offline import offline_uuid
from nostalgia.cli.main import main
from nostalgia.net.http import HttpClient


def test_adding_an_account_stores_the_deterministic_uuid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "account", "add-offline", "Jun"]) == 0
    assert offline_uuid("Jun") in capsys.readouterr().out

    assert main([*roots(tmp_path), "account", "list"]) == 0
    assert "Jun" in capsys.readouterr().out


def test_adding_the_same_account_twice_does_not_duplicate_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    main([*roots(tmp_path), "account", "add-offline", "jun"])
    capsys.readouterr()

    main([*roots(tmp_path), "account", "list"])

    assert len(capsys.readouterr().out.strip().splitlines()) == 1


def test_an_invalid_player_name_is_refused_with_exit_code_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "account", "add-offline", "x"]) == 1
    assert "không hợp lệ" in capsys.readouterr().err


def test_removing_an_account_that_does_not_exist_fails_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "account", "remove", "KhongCo"]) == 1
    assert "không có tài khoản" in capsys.readouterr().err

    main([*roots(tmp_path), "account", "add-offline", "Jun"])
    assert main([*roots(tmp_path), "account", "remove", "jun"]) == 0
    capsys.readouterr()
    main([*roots(tmp_path), "account", "list"])
    assert "chưa có tài khoản" in capsys.readouterr().out


def test_listing_installed_versions_needs_no_network(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "version", "--installed"]) == 0
    assert capsys.readouterr().out == ""


def test_doctor_on_a_version_that_was_never_installed_says_what_to_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([*roots(tmp_path), "doctor", "1.20.1"]) == 1
    captured = capsys.readouterr()
    assert "nostalgia install 1.20.1" in captured.out
    assert "1.20.1.json" in captured.err


def test_doctor_reports_a_complete_install_as_healthy(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_fake_version(server, server_state, http_client, tmp_path)
    capsys.readouterr()

    assert main([*roots(tmp_path), "doctor", VERSION_ID]) == 0
    assert "đủ" in capsys.readouterr().out


def test_doctor_notices_a_file_edited_in_place_only_with_the_flag(
    server: LocalHttpsServer,
    server_state: ServerState,
    http_client: HttpClient,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_fake_version(server, server_state, http_client, tmp_path)
    client_jar = make_paths(tmp_path).version_jar(VERSION_ID)
    edited = bytearray(client_jar.read_bytes())
    edited[0] ^= 0xFF
    client_jar.write_bytes(bytes(edited))
    capsys.readouterr()

    assert main([*roots(tmp_path), "doctor", VERSION_ID]) == 0
    capsys.readouterr()
    assert main([*roots(tmp_path), "doctor", VERSION_ID, "--verify-hashes"]) == 1
    assert "sai sha1" in capsys.readouterr().err
