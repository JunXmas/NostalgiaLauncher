"""Real files and a real stdin subprocess verify install rollback, EULA and world saving."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import pytest

from nostalgia.errors import IntegrityError, ServerError, SessionRevoked
from server_fixture import ServerAccountFixture, fake_java, server_launcher


def test_each_official_engine_installs_pinned_build_without_affecting_game(tmp_path: Path) -> None:
    launcher, http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    original = launcher.paths.instances_dir / "existing-world"
    original.mkdir(parents=True)
    (original / "level.dat").write_bytes(b"world untouched")
    for engine_id in (
        "paper",
        "purpur",
        "folia",
        "fabric",
        "arclight-forge",
        "arclight-neoforge",
        "arclight-fabric",
    ):
        assert manager.versions(engine_id) == ("1.21.1",)
        artifact = manager.builds(engine_id, "1.21.1")[0]
        server = manager.install("Cùng chơi", engine_id, "1.21.1", artifact.build_id)
        directory = manager.directory(server.server_id)
        assert (directory / "server.jar").read_bytes() == http_client.payload
        assert manager.server(server.server_id) == server
        assert not manager.properties(server.server_id).eula_accepted
    assert len(manager.list_servers()) == 7
    assert (original / "level.dat").read_bytes() == b"world untouched"


def test_corrupt_or_cancelled_install_never_registers_server(tmp_path: Path) -> None:
    launcher, http_client = server_launcher(tmp_path)
    manager = launcher.make_server_manager(ServerAccountFixture())
    http_client.corrupt = True
    with pytest.raises(IntegrityError):
        manager.install("Cùng chơi", "paper", "1.21.1", "132")
    assert manager.list_servers() == ()
    assert not any(launcher.paths.data_dir.joinpath("servers").iterdir())


@pytest.mark.parametrize("plan_name", ["Free", "Plus"])
def test_core_rejects_free_month_plan_and_paused_access(tmp_path: Path, plan_name: str) -> None:
    launcher, _http_client = server_launcher(tmp_path)
    account = ServerAccountFixture(plan_name)
    manager = launcher.make_server_manager(account)
    with pytest.raises(ServerError):
        manager.install("Host", "paper", "1.21.1", "132")
    assert manager.list_servers() == ()
    account.plan_name, account.paused = "Ultimate", True
    with pytest.raises(ServerError):
        manager.install("Host", "paper", "1.21.1", "132")


@pytest.mark.skipif(__import__("sys").platform == "win32", reason="fixture POSIX executable")
def test_process_ready_console_graceful_stop_and_session_revocation(tmp_path: Path) -> None:
    launcher, _http_client = server_launcher(tmp_path)
    account = ServerAccountFixture()
    manager = launcher.make_server_manager(account)
    server = manager.install("Host", "paper", "1.21.1", "132")
    output: list[str] = []
    with pytest.raises(ServerError, match="EULA"):
        manager.start(server.server_id, output.append)
    assert account.lease is None
    properties = replace(manager.properties(server.server_id), eula_accepted=True)
    manager.save_settings(server.server_id, properties, 1024, str(fake_java(tmp_path)))
    try:
        manager.start(server.server_id, output.append)
        deadline = time.monotonic() + 5
        while not manager.ready_id and time.monotonic() < deadline:
            time.sleep(0.01)
        assert manager.ready_id == server.server_id
        assert manager.room_connection().port == 25565
        with pytest.raises(ServerError):
            manager.start(server.server_id, output.append)
        with pytest.raises(ServerError):
            manager.save_settings(server.server_id, properties, 1024)
        with pytest.raises(ServerError):
            manager.command("say hello\nstop")
        manager.command("say hello")
        manager.heartbeat()
        manager.stop()
        directory = manager.directory(server.server_id)
        assert (directory / "saved-world.txt").read_text() == "saved"
        assert (directory / "commands.txt").read_text().splitlines() == ["say hello", "stop"]
        assert not manager.running_id and account.lease is None
        manager.start(server.server_id, output.append)
        account.revoked = True
        with pytest.raises(SessionRevoked):
            manager.heartbeat()
        assert not manager.running_id and not manager.ready_id
        with pytest.raises(SessionRevoked):
            manager.room_connection()
    finally:
        manager.shutdown()
