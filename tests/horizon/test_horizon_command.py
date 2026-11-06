"""Danh tính và texture Horizon không bị biến thành phiên Microsoft giả."""

import json
import sys
from pathlib import Path

import pytest

from nostalgia.account.model import Account
from nostalgia.errors import InstanceError
from nostalgia.horizon.command import HorizonCommand, build_horizon_command
from nostalgia.horizon.environment import build_horizon_environment
from nostalgia.horizon.model import HorizonBuild
from nostalgia.horizon.process import start_horizon
from nostalgia.launch.command import LaunchOptions
from nostalgia.skin.model import PlayerSkin


@pytest.mark.parametrize("account_kind", ["offline", "ely"])
def test_offline_and_ely_names_have_no_authentication_session(
    tmp_path: Path, account_kind: str
) -> None:
    account = Account("Player_Test", "f" * 32, account_kind, "never-send-ely-token")
    build = HorizonBuild("a" * 64, tmp_path / "bundle", "26.3", 25)
    command = build_horizon_command(build, account, LaunchOptions(tmp_path / "game"))
    assert "--name" in command.argv and "Player_Test" in command.argv
    assert "--session-stdin" not in command.argv
    assert not command.standard_input
    assert "never-send-ely-token" not in repr(command)
    assert "java" not in command.argv and "-cp" not in command.argv


def test_microsoft_secret_uses_stdin_and_never_argv_or_repr(tmp_path: Path) -> None:
    account = Account("Player_Test", "f" * 32, "microsoft", "private-access-token")
    build = HorizonBuild("a" * 64, tmp_path / "bundle", "26.3", 25)
    command = build_horizon_command(build, account, LaunchOptions(tmp_path / "game"))
    assert json.loads(command.standard_input)["access_token"] == account.access_token
    assert json.loads(command.standard_input)["user_type"] == "msa"
    assert account.access_token not in repr(command)
    assert all(account.access_token not in argument for argument in command.argv)


def test_invalid_offline_name_is_rejected_before_start(tmp_path: Path) -> None:
    build = HorizonBuild("a" * 64, tmp_path, "26.3", 25)
    with pytest.raises(InstanceError, match="player name"):
        build_horizon_command(
            build, Account("bad name", "f" * 32, "offline"), LaunchOptions(tmp_path)
        )


def test_native_child_receives_local_skin_and_redacts_session_output(tmp_path: Path) -> None:
    outputs: list[str] = []
    script = (
        "import os,sys; print(sys.stdin.read()); "
        "print(os.environ['HORIZON_OFFLINE_SKIN']); "
        "print(os.environ['HORIZON_OFFLINE_SKIN_MODEL']); "
        "print(os.environ['HORIZON_TELEMETRY_URL']); "
        "print(os.environ['HORIZON_NO_HEARTBEAT']); "
        "print(os.environ['HORIZON_COSMETICS'])"
    )
    command = HorizonCommand(
        (sys.executable, "-c", script),
        tmp_path,
        b"private-access-token",
        frozenset({"private-access-token"}),
        PlayerSkin(tmp_path / "ely.png", True),
    )
    game_process = start_horizon(command, on_output=outputs.append)
    assert game_process.wait(timeout=10) == 0
    assert outputs == ["***", str(tmp_path / "ely.png"), "slim", "off", "1", "0"]


def test_inherited_player_session_and_skin_are_not_reused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for field in (
        "HORIZON_SESSION_FILE",
        "HORIZON_PLAYER_NAME",
        "HORIZON_OFFLINE_SKIN",
        "HORIZON_OFFLINE_CAPE",
    ):
        monkeypatch.setenv(field, "another-player")
    environment = build_horizon_environment(tmp_path)
    assert "HORIZON_SESSION_FILE" not in environment
    assert "HORIZON_PLAYER_NAME" not in environment
    assert "HORIZON_OFFLINE_SKIN" not in environment
    assert "HORIZON_OFFLINE_CAPE" not in environment
    assert environment["HORIZON_NO_DISCORD"] == "1"
