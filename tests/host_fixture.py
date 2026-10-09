"""Host integration harness: real disk/snapshots/Qt, controlled JVM, relay and upload edges."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QObject

from nostalgia.api import Instance, Launcher, RoomStatus, SyncSnapshot
from nostalgia.errors import MultiplayerError
from nostalgia.operations.cancellation import CancelToken
from nostalgia.storage.files import atomic_write_json
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.host_bridge import HostBridge
from nostalgia.ui.multiplayer_bridge import MultiplayerBridge
from nostalgia.ui.room_sync_bridge import RoomSyncBridge
from nostalgia.ui.social_bridge import SocialBridge
from nostalgia.ui.worker import wait_for_background
from social_fixture import SocialFixture


class ControlledGame:
    def __init__(self) -> None:
        self.done = threading.Event()
        self.exit_code = 0
        self.output: Callable[[str], None] = lambda _line: None

    def wait(self) -> int:
        assert self.done.wait(15), "test did not close its fake JVM"
        return self.exit_code

    def stop(self) -> None:
        self.done.set()


class ControlledRoom:
    def __init__(self) -> None:
        self.status = RoomStatus()
        self.on_status: Callable[[RoomStatus], None] = lambda _status: None
        self.detect_modes: list[bool] = []
        self.ports: list[int] = []
        self.stops = 0

    def start_hosting(self, *, auto_detect: bool = True) -> None:
        self.detect_modes.append(auto_detect)
        self.apply(RoomStatus(role="waiting_world", room_code="ABCDEFABCDEFGHJKMN"))

    def apply(self, status: RoomStatus) -> None:
        self.status = status
        self.on_status(status)

    def hosting(self) -> None:
        self.apply(
            RoomStatus(
                role="hosting",
                room_code="ABCDEFABCDEFGHJKMN",
                world_name="World",
                host_ticket="opaque-ticket",
            )
        )

    def supply_lan_port(self, port: int) -> None:
        self.ports.append(port)

    def set_locked(self, locked: bool) -> None:
        self.apply(replace(self.status, locked=locked))

    def stop(self) -> None:
        self.stops += 1
        self.apply(RoomStatus())


class ControlledUpload:
    def __init__(self) -> None:
        self.entered, self.release = threading.Event(), threading.Event()
        self.fail = False
        self.received: list[SyncSnapshot] = []
        self.payloads: list[dict[str, bytes]] = []

    def publish(
        self,
        room_code: str,
        host_ticket: str,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken | None = None,
    ) -> None:
        assert room_code == "ABCDEFABCDEFGHJKMN" and host_ticket == "opaque-ticket"
        self.received.append(snapshot)
        self.payloads.append(
            {
                f.relative_path: (snapshot.folder / f.relative_path).read_bytes()
                for f in snapshot.manifest.files
            }
        )
        self.entered.set()
        assert self.release.wait(15), "test did not release its upload"
        if cancel_token is not None:
            cancel_token.raise_if_cancelled()
        if self.fail:
            raise MultiplayerError("403: Plus expired")

    def resolve(self, room_code: str) -> None:
        del room_code

    def download(self, room_code: str, sync_file: object) -> bytes:
        del room_code, sync_file
        raise AssertionError("host must not download")


class HostRig:
    def __init__(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, plus_enabled: bool = True
    ) -> None:
        self.launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
        self.launcher.add_offline_account("MinecraftName")
        atomic_write_json(
            self.launcher.paths.version_json("1.20.1"),
            {"id": "1.20.1", "mainClass": "Main", "libraries": []},
        )
        version_id = "1.20.1-forge-47.4.23"
        atomic_write_json(
            self.launcher.paths.version_json(version_id),
            {
                "id": version_id,
                "inheritsFrom": "1.20.1",
                "mainClass": "Main",
                "libraries": [{"name": "net.minecraftforge:fmlloader:1.20.1-47.4.23"}],
            },
        )
        self.launcher.create_instance(Instance("other", "1.20.1", "Other pack"))
        selected = self.launcher.create_instance(
            Instance("chosen", version_id, "Chosen Forge pack", nos_client_enabled=True)
        )
        self.source = self.launcher.instance_game_dir(selected)
        (self.source / "mods").mkdir()
        (self.source / "mods/selected.jar").write_bytes(b"selected")
        self.game, self.room, self.upload = ControlledGame(), ControlledRoom(), ControlledUpload()
        self.launched: list[str] = []
        self.prepare_entered, self.prepare_release = threading.Event(), threading.Event()
        self.prepare_release.set()
        self.launch_error = False

        def install(_launcher: Launcher, version_id: str, **_kwargs: Any) -> None:
            assert version_id == selected.version_id
            self.prepare_entered.set()
            assert self.prepare_release.wait(15)

        def inject(_launcher: Launcher, instance: Instance) -> None:
            assert instance.instance_id == "chosen"
            (self.source / "mods/nos.jar").write_bytes(b"injected before capture")

        def launch(_launcher: Launcher, instance_id: str, account_id: str, **kwargs: Any) -> Any:
            assert account_id and instance_id == "chosen"
            if self.launch_error:
                raise MultiplayerError("JVM could not start")
            self.launched.append(instance_id)
            self.game.output = kwargs["on_output"]
            self.game.output("[Server thread/INFO]: Started serving on 51234")
            return self.game

        def room_service(_launcher: Launcher, **kwargs: Any) -> Any:
            self.room.on_status = kwargs["on_status"]
            return self.room

        monkeypatch.setattr(Launcher, "install_version", install)
        monkeypatch.setattr(Launcher, "prepare_nos_client", inject)
        monkeypatch.setattr(Launcher, "launch_instance", launch)
        monkeypatch.setattr(Launcher, "make_room_service", room_service)
        self.parent = QObject()
        self.bridge: Any = LauncherBridge(self.launcher, self.parent)
        self.multiplayer: Any = MultiplayerBridge(self.launcher, self.parent)
        self.sync: Any = RoomSyncBridge(
            self.launcher, self.bridge, self.multiplayer, self.upload, self.parent
        )
        self.social_gateway = SocialFixture()
        self.social_gateway.access_token = "a" * 64
        self.social_gateway.snapshot = replace(
            self.social_gateway.snapshot,
            account=replace(self.social_gateway.snapshot.account, plus_lifetime=True),
        )
        self.social: Any = SocialBridge(
            self.social_gateway, self.multiplayer, self.sync, self.parent, plus_enabled=plus_enabled
        )
        self.social._snapshot = self.social_gateway.snapshot
        self.host: Any = HostBridge(
            self.launcher,
            self.bridge,
            self.multiplayer,
            self.sync,
            self.social,
            plus_enabled=plus_enabled,
            parent=self.parent,
        )
        self.host.connect_workflow()

    def close(self) -> None:
        self.host.stop()
        self.prepare_release.set()
        self.upload.release.set()
        self.game.done.set()
        self.social.shutdown()
        self.sync.cancel()
        wait_for_background()


@pytest.fixture
def host_rig(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[HostRig]:
    rig = HostRig(tmp_path, monkeypatch)
    try:
        yield rig
    finally:
        rig.close()
