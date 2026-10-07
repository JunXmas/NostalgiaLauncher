"""Cancelled preparation/uploads and dead JVMs cannot reopen a room or publish invitations."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
from test_bridges import wait_until

from host_fixture import HostRig
from host_fixture import host_rig as host_rig
from nostalgia.errors import MultiplayerError
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


def test_cancel_preparation_does_not_launch_or_host(host_rig: HostRig) -> None:
    rig = host_rig
    rig.prepare_release.clear()
    assert rig.host.start("chosen", True)
    wait_until(rig.prepare_entered.is_set)
    assert rig.host.details["active"] and not rig.room.detect_modes
    rig.host.stop()
    rig.prepare_release.set()
    wait_until(lambda: not rig.bridge.busy)
    assert not rig.launched and not rig.upload.received and not rig.room.detect_modes
    assert rig.room.status.role == "idle" and not rig.host.details["active"]


@pytest.mark.parametrize("cause", ["stop", "crash", "logout", "relay_lost"])
def test_cancel_upload_discards_late_completion(host_rig: HostRig, cause: str) -> None:
    rig = host_rig
    assert rig.host.start("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "waiting_world")
    rig.room.hosting()
    wait_until(rig.upload.entered.is_set)
    if cause == "stop":
        rig.host.stop()
    elif cause == "crash":
        rig.game.exit_code = 1
        rig.game.done.set()
    elif cause == "logout":
        rig.social._reset_session("Revoked on another machine")
    else:
        rig.room.stop()
    wait_until(lambda: not rig.host.details["active"])
    rig.upload.release.set()
    wait_until(lambda: not rig.sync.busy)
    assert rig.room.status.role == "idle" and rig.host.details["stage"] == "idle"
    rig.social.inviteFriend("misa")
    assert not rig.social_gateway.invited
    if cause != "crash":
        assert rig.bridge.gameRunning


def test_snapshot_error_and_launch_error_never_open_room(
    host_rig: HostRig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = host_rig
    capture = rig.launcher.__class__.capture_room_modpack

    def denied(*_args: object, **_kwargs: object) -> None:
        raise MultiplayerError("unsafe modpack link")

    monkeypatch.setattr(rig.launcher.__class__, "capture_room_modpack", denied)
    assert rig.host.start("chosen", True)
    wait_until(lambda: not rig.host.details["active"] and not rig.bridge.busy)
    assert "unsafe" in rig.host.details["note"]
    assert not rig.launched and not rig.room.detect_modes
    monkeypatch.setattr(rig.launcher.__class__, "capture_room_modpack", capture)
    rig.launch_error = True
    assert rig.host.start("chosen", True)
    wait_until(lambda: not rig.host.details["active"] and not rig.bridge.busy)
    assert "JVM" in rig.host.details["note"] and not rig.room.detect_modes
    assert not list(rig.launcher.paths.data_dir.glob("room-host-*"))


def test_paused_and_free_accounts_cannot_force_sync(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = HostRig(tmp_path, monkeypatch, plus_enabled=False)
    try:
        assert not rig.host.syncAvailable
        assert not rig.host.start("chosen", True)
        assert not rig.launched and not rig.room.detect_modes
        rig.host._plus_enabled = True
        rig.social._plus_enabled = True
        rig.social._snapshot = replace(
            rig.social_gateway.snapshot,
            account=replace(rig.social_gateway.snapshot.account, plus_lifetime=False),
        )
        assert not rig.host.syncAvailable
        assert not rig.host.start("chosen", True)
        assert not rig.launched
    finally:
        rig.close()


def test_running_busy_storage_or_missing_pack_rejected(host_rig: HostRig) -> None:
    rig = host_rig
    assert not rig.host.start("missing", False)
    rig.bridge.setStorageBusy(True)
    assert not rig.host.start("chosen", False)
    rig.bridge.setStorageBusy(False)
    rig.prepare_release.clear()
    assert rig.host.start("chosen", False)
    assert not rig.host.start("chosen", False)
    rig.prepare_release.set()
    wait_until(lambda: rig.bridge.gameRunning)
    rig.host.stop()
    wait_for_background(0.01)
    assert not rig.host.start("chosen", False)
    assert rig.launched == ["chosen"]
