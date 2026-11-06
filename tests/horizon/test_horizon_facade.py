"""Kho bản chơi native, đường chạy offline và giới hạn không dùng mod Java."""

from dataclasses import replace
from pathlib import Path
from typing import Any, NoReturn
from unittest.mock import Mock

import pytest

from nostalgia.account.model import Account
from nostalgia.account.store import save_accounts
from nostalgia.api import Instance, Launcher
from nostalgia.errors import ContentError, InstanceError, NostalgiaError
from nostalgia.horizon.command import HorizonCommand
from nostalgia.horizon.model import HorizonBuild
from nostalgia.instance.store import list_instances, load_instance
from nostalgia.launch.game_process import GameProcess
from nostalgia.repo.version_repo import VersionRepository
from nostalgia.skin.model import PlayerSkin
from nostalgia.storage.files import atomic_write_json


@pytest.fixture
def native_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Launcher:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "config")
    build = HorizonBuild("a" * 64, tmp_path / "bundle", "26.3", 25)
    monkeypatch.setattr("nostalgia.facade.horizon.load_build", lambda *_args: build)
    monkeypatch.setattr("nostalgia.facade.horizon.check_resources", lambda *_args: True)
    launcher.create_instance(
        Instance(
            "native",
            "horizon-26.3",
            runtime_kind="horizon",
            horizon_build_id=build.build_id,
        )
    )
    return launcher


def test_existing_java_instance_and_native_pin_survive_reload(native_launcher: Launcher) -> None:
    launcher = native_launcher
    atomic_write_json(launcher.paths.instance_json("old-java"), {"version_id": "1.21.11"})
    assert load_instance(launcher.paths, "old-java").runtime_kind == "java"
    instance = load_instance(launcher.paths, "native")
    launcher.save_instance(replace(instance, display_name="Renamed"))
    assert load_instance(launcher.paths, "native").horizon_build_id == "a" * 64
    assert load_instance(launcher.paths, "native").runtime_kind == "horizon"
    atomic_write_json(
        launcher.paths.instance_json("corrupt"),
        {
            "version_id": "26.3",
            "runtime_kind": "unknown",
        },
    )
    assert {value.instance_id for value in list_instances(launcher.paths)} == {"old-java", "native"}


def test_native_version_id_cannot_fall_back_to_a_java_install(native_launcher: Launcher) -> None:
    atomic_write_json(
        native_launcher.paths.version_json("26.3"), {"id": "26.3", "mainClass": "JavaOnly"}
    )
    instance = load_instance(native_launcher.paths, "native")
    assert instance.version_id == "horizon-26.3"
    with pytest.raises(NostalgiaError):
        VersionRepository(native_launcher.paths).load_version_meta(instance.version_id)


def test_cached_native_preparation_and_offline_launch_need_no_http(
    native_launcher: Launcher, monkeypatch: pytest.MonkeyPatch
) -> None:
    def deny_http() -> NoReturn:
        pytest.fail("a prepared offline instance must not request the network")

    launcher = replace(native_launcher, make_http_client=deny_http)
    account = launcher.add_offline_account("OfflineQA")
    commands: list[HorizonCommand] = []
    game_process: GameProcess = Mock(spec=GameProcess)

    def capture(command: HorizonCommand, **_options: Any) -> GameProcess:
        commands.append(command)
        return game_process

    monkeypatch.setattr("nostalgia.facade.horizon.start_horizon", capture)
    instance = load_instance(launcher.paths, "native")
    launcher.prepare_horizon_instance(instance)
    assert launcher.launch_instance(instance.instance_id, account.account_id) is game_process
    assert commands[0].argv[-2:] == ("--name", "OfflineQA")
    assert not commands[0].standard_input
    assert not launcher.nos_client_supported(instance)
    assert launcher.describe_play_choices(instance.instance_id).quick_play.worlds


def test_ely_skin_uses_public_texture_and_never_ely_authentication(
    native_launcher: Launcher, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    account = Account("ElySkinQA", "f" * 32, "ely", "secret-ely-token")
    save_accounts(native_launcher.paths.accounts_json, (account,))
    player_skin = PlayerSkin(tmp_path / "ely.png", True, tmp_path / "cape.png")
    monkeypatch.setattr(
        "nostalgia.facade.horizon.refresh_ely_skin", lambda *_args, **_kw: player_skin
    )

    def deny_auth(*_args: Any, **_options: Any) -> NoReturn:
        pytest.fail("Horizon must not forward or renew an Ely authentication session")

    monkeypatch.setattr("nostalgia.facade.accounts.refresh_ely_account", deny_auth)
    commands: list[HorizonCommand] = []
    monkeypatch.setattr(
        "nostalgia.facade.horizon.start_horizon", lambda command, **_kw: commands.append(command)
    )
    native_launcher.launch_instance("native", account.account_id)
    assert commands[0].player_skin == player_skin
    assert commands[0].argv[-2:] == ("--name", account.player_name)
    assert not commands[0].standard_input
    assert account.access_token not in repr(commands[0])


def test_native_never_exports_as_java_or_installs_java_content(
    native_launcher: Launcher, tmp_path: Path
) -> None:
    with pytest.raises(ContentError, match="Java mods"):
        native_launcher.describe_content_target("native")
    destination = tmp_path / "native.mrpack"
    with pytest.raises(InstanceError, match="Java modpack"):
        native_launcher.export_instance_modpack("native", destination, "mrpack")
    assert not destination.exists()


def test_new_native_instance_refuses_existing_worlds(
    native_launcher: Launcher, tmp_path: Path
) -> None:
    game_dir = tmp_path / "existing"
    (game_dir / "saves" / "valuable-world").mkdir(parents=True)
    sentinel = game_dir / "saves" / "valuable-world" / "level.dat"
    sentinel.write_bytes(b"keep unchanged")
    with pytest.raises(InstanceError, match="empty game folder"):
        native_launcher.create_instance(
            Instance(
                "separate",
                "horizon-26.3",
                runtime_kind="horizon",
                horizon_build_id="a" * 64,
                game_dir_override=str(game_dir),
            )
        )
    assert sentinel.read_bytes() == b"keep unchanged"
    assert not native_launcher.paths.instance_json("separate").exists()
