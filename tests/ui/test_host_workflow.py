"""Selected pack is frozen after injection, then invitations wait for server upload commit."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
from test_bridges import wait_until

from host_fixture import HostRig
from host_fixture import host_rig as host_rig

pytestmark = pytest.mark.usefixtures("qt_app")


def test_selected_pack_launch_snapshot_and_invite_gate(host_rig: HostRig) -> None:
    rig = host_rig
    assert rig.host.start("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "waiting_world")
    assert rig.launched == ["chosen"]
    assert rig.room.detect_modes == [False]
    wait_until(lambda: rig.room.ports == [51234])  # early output before gameStarted
    rig.host._lan_opened("other", 54321)
    assert rig.room.ports == [51234]
    snapshot = rig.host._snapshot
    assert snapshot is not None
    assert (
        snapshot.manifest.game_version,
        snapshot.manifest.loader_kind,
        snapshot.manifest.loader_version,
    ) == ("1.20.1", "forge", "47.4.23")
    (rig.source / "mods/selected.jar").write_bytes(b"changed after game launch")
    rig.room.hosting()
    wait_until(rig.upload.entered.is_set)
    assert rig.host.details["stage"] == "publishing" and not rig.sync.hostReady
    assert rig.multiplayer.room_snapshot().locked
    rig.social.inviteFriend("misa")  # direct Python call also gated, not just disabled QML
    assert not rig.social_gateway.invited
    assert rig.upload.payloads == [
        {"mods/nos.jar": b"injected before capture", "mods/selected.jar": b"selected"}
    ]
    rig.upload.release.set()
    wait_until(lambda: rig.sync.hostReady and not rig.sync.busy)
    assert rig.host.details["stage"] == "ready" and not rig.multiplayer.room_snapshot().locked
    rig.social.inviteFriend("misa")
    wait_until(lambda: rig.social_gateway.invited == ["misa"] and not rig.social.busy)
    assert len(rig.upload.received) == 1
    assert rig.bridge.gameRunning
    rig.game.done.set()
    wait_until(lambda: not rig.host.details["active"] and not rig.bridge.busy)
    assert rig.room.status.role == "idle" and not snapshot.folder.exists()


def test_upload_failure_keeps_game_and_retries_original_frozen_pack(host_rig: HostRig) -> None:
    rig = host_rig
    rig.upload.fail = True
    rig.upload.release.set()
    assert rig.host.start("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "waiting_world")
    rig.room.hosting()
    wait_until(lambda: rig.host.details["stage"] == "error" and not rig.sync.busy)
    assert (
        rig.bridge.gameRunning and rig.multiplayer.room_snapshot().locked and not rig.sync.hostReady
    )
    rig.social.inviteFriend("misa")
    assert not rig.social_gateway.invited
    (rig.source / "mods/selected.jar").unlink()
    rig.upload.fail = False
    rig.host.retryShare()
    wait_until(lambda: rig.host.details["stage"] == "ready" and not rig.sync.busy)
    assert rig.upload.received[0] == rig.upload.received[1]
    assert rig.upload.payloads[0] == rig.upload.payloads[1]
    assert rig.launched == ["chosen"]


def test_free_host_launches_and_waits_for_lan_without_sync(host_rig: HostRig) -> None:
    rig = host_rig
    assert rig.host.start("chosen", False)
    wait_until(lambda: rig.host.details["stage"] == "waiting_world")
    assert not rig.sync.hostReady and not rig.upload.received
    rig.room.hosting()
    assert rig.host.details["stage"] == "ready" and rig.sync.hostReady
    assert rig.bridge.gameRunning and not rig.upload.received
