"""Phòng chờ mời và đồng bộ được trước JVM; hủy không được khởi chạy ngầm."""

from dataclasses import replace

import pytest
from test_bridges import wait_until

from host_fixture import HostRig
from host_fixture import host_rig as host_rig

pytestmark = pytest.mark.usefixtures("qt_app")


def ready_lobby(rig: HostRig) -> None:
    rig.room.apply(
        replace(rig.room.status, host_ticket="opaque-ticket", world_name="World", world_ready=False)
    )


def test_invite_and_share_before_launch_then_reuse_frozen_pack(host_rig: HostRig) -> None:
    rig = host_rig
    rig.upload.release.set()
    assert rig.host.createRoom("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "lobby")
    ready_lobby(rig)
    wait_until(lambda: rig.sync.hostReady and not rig.sync.busy)
    assert not rig.launched and not rig.bridge.gameRunning
    assert rig.host.details["stage"] == "lobby"
    rig.social.inviteFriend("misa")
    wait_until(lambda: rig.social_gateway.invited == ["misa"])
    rig.host.launchRoom()
    wait_until(lambda: rig.launched == ["chosen"] and rig.room.ports == [51234])
    assert rig.room.detect_modes == [False], "one room only; launching must not replace the room"
    rig.room.hosting()
    wait_until(lambda: rig.host.details["stage"] == "ready")
    assert len(rig.upload.received) == 1
    assert rig.sync.hostReady


def test_late_room_updates_do_not_republish_ready_modpack(host_rig: HostRig) -> None:
    rig = host_rig
    rig.upload.release.set()
    assert rig.host.createRoom("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "lobby")
    ready_lobby(rig)
    wait_until(lambda: rig.sync.hostReady and not rig.sync.busy)
    assert len(rig.upload.received) == 1
    # Dịch vụ thật gửi cập nhật khóa/phòng từ asyncio sau khi worker đã rảnh.
    rig.room.apply(replace(rig.room.status, locked=False, joiner_count=1))
    assert rig.host.details["stage"] == "lobby"
    assert rig.sync.hostReady and not rig.sync.busy
    assert len(rig.upload.received) == 1


def test_cancel_lobby_releases_worker_and_snapshot_without_launch(host_rig: HostRig) -> None:
    rig = host_rig
    assert rig.host.createRoom("chosen", False)
    wait_until(lambda: rig.host.details["stage"] == "lobby")
    ready_lobby(rig)
    assert rig.sync.hostReady and not rig.launched
    rig.host.stop()
    wait_until(lambda: not rig.bridge.busy)
    assert not rig.host.details["active"] and not rig.launched


def test_game_can_wait_for_lan_without_publishing_an_invalid_port(
    host_rig: HostRig, monkeypatch: pytest.MonkeyPatch
) -> None:
    rig = host_rig

    def launch(_launcher: object, instance_id: str, _account_id: str, **kwargs: object) -> object:
        rig.launched.append(instance_id)
        rig.game.output = kwargs["on_output"]  # type: ignore[assignment]
        return rig.game

    monkeypatch.setattr(type(rig.launcher), "launch_instance", launch)
    failures: list[str] = []
    rig.multiplayer.failed.connect(failures.append)
    assert rig.host.createRoom("chosen", False)
    wait_until(lambda: rig.host.details["stage"] == "lobby")
    ready_lobby(rig)
    rig.host.launchRoom()
    wait_until(lambda: rig.host.details["stage"] == "waiting_world")
    rig.host._lan_opened("chosen", 0)
    assert rig.room.ports == [] and not failures
    rig.game.output("[Server thread/INFO]: Started serving on 51234")
    wait_until(lambda: rig.room.ports == [51234])


def test_denied_sync_cannot_launch_or_invite_then_can_retry(host_rig: HostRig) -> None:
    rig = host_rig
    rig.upload.fail = True
    rig.upload.release.set()
    assert rig.host.createRoom("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "lobby")
    ready_lobby(rig)
    wait_until(lambda: rig.host.details["stage"] == "error" and not rig.sync.busy)
    rig.host.launchRoom()
    rig.social.inviteFriend("misa")
    assert not rig.launched and not rig.social_gateway.invited
    rig.upload.fail = False
    rig.host.retryShare()
    wait_until(lambda: rig.sync.hostReady)
    assert rig.host.details["stage"] == "lobby" and not rig.launched


def test_changed_host_modpack_does_not_launch_after_guest_received_snapshot(
    host_rig: HostRig,
) -> None:
    rig = host_rig
    rig.upload.release.set()
    assert rig.host.createRoom("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "lobby")
    ready_lobby(rig)
    wait_until(lambda: rig.sync.hostReady and not rig.sync.busy)
    (rig.source / "mods/selected.jar").write_bytes(b"changed after invite")
    rig.host.launchRoom()
    wait_until(lambda: not rig.bridge.busy and not rig.host.details["active"])
    assert not rig.launched and not rig.multiplayer.active
    assert "thay đổi" in rig.host.details["note"]
