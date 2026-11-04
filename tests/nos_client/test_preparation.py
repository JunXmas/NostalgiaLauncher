"""Đúng luồng bấm Chơi: cập nhật trước khi chụp bộ mod, không hạ bản đang cài khi mất mạng."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from local_https_server import LocalHttpsServer, ServerState
from nos_fixture import build_nos_jar, build_nos_release
from nostalgia.api import Instance, Launcher
from nostalgia.errors import Cancelled, ContentError, NetworkError
from nostalgia.modrepair.transaction import lock_mods
from nostalgia.nos_client import release
from nostalgia.operations.cancellation import CancelToken
from nostalgia.operations.progress import Progress
from nostalgia.ui.game_launch import prepare_game
from test_api import make_launcher


@pytest.fixture
def nos_launcher(
    server: LocalHttpsServer,
    server_state: ServerState,
    tmp_path: Path,
    certificate_pair: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> Launcher:
    monkeypatch.setattr(release, "GITHUB_API_BASE", server.url(""))
    launcher = make_launcher(server, server_state, tmp_path, certificate_pair)
    launcher.create_instance(
        Instance("nos", "fabric-loader-0.19.3-1.21.11", nos_client_enabled=True)
    )
    return launcher


def test_play_preparation_installs_new_release_before_mod_snapshot(
    nos_launcher: Launcher,
    server: LocalHttpsServer,
    server_state: ServerState,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mods = nos_launcher.paths.instance_dir("nos") / "mods"
    mods.mkdir()
    (mods / "nosclient-0.4.1.jar").write_bytes(build_nos_jar(mod_version="0.4.1"))
    body = build_nos_jar(mod_version="0.4.3")
    url = server_state.add("/new.jar", body)
    server_state.add(
        "/repos/JunXmas/nos-client/releases",
        json.dumps(
            [
                build_nos_release("nos-client-0.4.3.jar", server.url(url), body),
            ]
        ).encode(),
    )

    def install(_self: Launcher, _version_id: str, **_kwargs: object) -> None:
        pass

    monkeypatch.setattr(Launcher, "install_version", install)
    events: list[Progress] = []
    prepare_game(nos_launcher, "nos", events.append, None)
    assert (mods / "nos-client-0.4.3.jar").read_bytes() == body
    assert not (mods / "nosclient-0.4.1.jar").exists()
    assert len(list(mods.glob("*.jar"))) == 1
    assert any("Nos Client" in event.stage for event in events)


def test_offline_keeps_newer_manually_installed_client(
    nos_launcher: Launcher,
    server_state: ServerState,
) -> None:
    mods = nos_launcher.paths.instance_dir("nos") / "mods"
    mods.mkdir()
    installed = mods / "MyNos.jar"
    installed.write_bytes(build_nos_jar())
    cache = nos_launcher.paths.data_dir / "nos-client"
    cache.mkdir()
    (cache / "nos-client-0.4.1.jar").write_bytes(build_nos_jar(mod_version="0.4.1"))
    server_state.add("/repos/JunXmas/nos-client/releases", b"[]", status=404)
    before = installed.stat().st_mtime_ns
    instance = nos_launcher.list_instances()[0]
    nos_launcher.prepare_nos_client(instance)
    assert list(mods.iterdir()) == [installed]
    assert installed.stat().st_mtime_ns == before


def test_first_install_without_release_reports_error(
    nos_launcher: Launcher,
    server_state: ServerState,
) -> None:
    server_state.add("/repos/JunXmas/nos-client/releases", b"[]", status=404)
    with pytest.raises(NetworkError, match="Nos Client"):
        nos_launcher.prepare_nos_client(nos_launcher.list_instances()[0])
    assert not list(nos_launcher.paths.instance_dir("nos").glob("mods/*.jar"))


def test_preparation_cancellation_does_not_launch_or_modify_mods(
    nos_launcher: Launcher,
    server_state: ServerState,
) -> None:
    cancel_token = CancelToken()
    cancel_token.cancel()
    with pytest.raises(Cancelled):
        nos_launcher.prepare_nos_client(nos_launcher.list_instances()[0], cancel_token=cancel_token)
    assert not list(nos_launcher.paths.instance_dir("nos").glob("mods/*.jar"))
    assert all(route.requests == 0 for route in server_state.routes.values())


def test_new_release_needing_newer_loader_uses_compatible_previous_client(
    nos_launcher: Launcher,
    server: LocalHttpsServer,
    server_state: ServerState,
) -> None:
    cache = nos_launcher.paths.data_dir / "nos-client"
    cache.mkdir()
    previous = build_nos_jar()
    (cache / "nos-client-0.4.2.jar").write_bytes(previous)
    body = build_nos_jar(mod_version="0.4.3", loader_version=">=0.20.0")
    url = server_state.add("/new.jar", body)
    server_state.add(
        "/repos/JunXmas/nos-client/releases",
        json.dumps(
            [
                build_nos_release("nos-client-0.4.3.jar", server.url(url), body),
            ]
        ).encode(),
    )
    nos_launcher.prepare_nos_client(nos_launcher.list_instances()[0])
    mods = nos_launcher.paths.instance_dir("nos") / "mods"
    assert (mods / "nos-client-0.4.2.jar").read_bytes() == previous
    assert not (mods / "nos-client-0.4.3.jar").exists()


def test_unsupported_game_does_not_fetch_or_install(
    nos_launcher: Launcher, server_state: ServerState
) -> None:
    instance = replace(nos_launcher.list_instances()[0], version_id="fabric-loader-0.20.1-26.2")
    nos_launcher.prepare_nos_client(instance)
    assert not list(nos_launcher.paths.instance_dir("nos").glob("mods/*.jar"))
    assert all(route.requests == 0 for route in server_state.routes.values())


def test_recovery_does_not_enter_another_mod_transaction(nos_launcher: Launcher) -> None:
    instance = nos_launcher.list_instances()[0]
    with lock_mods(nos_launcher.instance_game_dir(instance)), pytest.raises(ContentError):
        nos_launcher.recover_interrupted_mod_change(instance.instance_id)
