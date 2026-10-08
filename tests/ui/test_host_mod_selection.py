"""Lựa chọn chia sẻ được chụp lúc launch; kết quả đọc muộn không thay bản vừa chọn."""

import threading
from pathlib import Path

import pytest
from test_bridges import wait_until

from host_fixture import HostRig
from host_fixture import host_rig as host_rig
from nostalgia.api import Launcher
from nostalgia.errors import MultiplayerError
from nostalgia.ui.host_selection import HostModSelection
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


def test_unselected_mod_stays_on_host_and_is_not_published(host_rig: HostRig) -> None:
    rig = host_rig
    selection = rig.host._mod_selection
    selection.selectInstance("chosen")
    wait_until(lambda: bool(selection.ready))
    selection.setShared("mods/selected.jar", False)
    assert rig.host.start("chosen", True)
    wait_until(lambda: rig.host.details["stage"] == "waiting_world")
    assert (rig.source / "mods/selected.jar").read_bytes() == b"selected"
    assert rig.launcher.load_room_share_options("chosen") == frozenset({"mods/selected.jar"})
    snapshot = rig.host._snapshot
    assert snapshot is not None
    assert [sync_file.relative_path for sync_file in snapshot.manifest.files] == ["mods/nos.jar"]
    rig.room.hosting()
    wait_until(rig.upload.entered.is_set)
    assert rig.upload.payloads == [{"mods/nos.jar": b"injected before capture"}]
    rig.upload.release.set()
    wait_until(lambda: rig.host.details["stage"] == "ready")


def test_host_cannot_launch_while_current_mod_list_is_loading(
    host_rig: HostRig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rig = host_rig
    entered, release = threading.Event(), threading.Event()
    original = Launcher.list_room_share_mods

    def read(self: Launcher, instance_id: str) -> object:
        entered.set()
        assert release.wait(5)
        return original(self, instance_id)

    monkeypatch.setattr(Launcher, "list_room_share_mods", read)
    try:
        rig.host._mod_selection.selectInstance("chosen")
        wait_until(entered.is_set)
        assert not rig.host.start("chosen", True) and not rig.launched
    finally:
        release.set()
        wait_until(lambda: rig.host._mod_selection.ready)


def test_old_worker_cannot_enable_launch_for_new_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    launcher = Launcher.for_data_dir(tmp_path)
    release_first, release_second = threading.Event(), threading.Event()
    entered_second = threading.Event()

    def read(_self: Launcher, instance_id: str) -> tuple[object, ...]:
        if instance_id == "a":
            assert release_first.wait(5)
        else:
            entered_second.set()
            assert release_second.wait(5)
        return ()

    monkeypatch.setattr(Launcher, "list_room_share_mods", read)
    selection = HostModSelection(launcher)
    try:
        selection.selectInstance("a")
        selection.selectInstance("b")
        wait_until(entered_second.is_set)
        release_first.set()
        wait_until(lambda: not selection.busy)
        assert not selection.ready and selection.excluded_for("b") is None
        release_second.set()
        wait_until(lambda: bool(selection.ready))
        assert selection.excluded_for("b") == frozenset()
        assert selection.excluded_for("a") is None
    finally:
        release_first.set()
        release_second.set()
        wait_for_background()


def test_failed_read_does_not_silently_share_every_mod(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = Launcher.for_data_dir(tmp_path)

    def read(_self: Launcher, _instance_id: str) -> tuple[object, ...]:
        raise MultiplayerError("disk unavailable")

    monkeypatch.setattr(Launcher, "list_room_share_mods", read)
    selection = HostModSelection(launcher)
    failures: list[str] = []
    selection.failed.connect(failures.append)
    selection.selectInstance("a")
    wait_until(lambda: bool(failures))
    assert not selection.ready and selection.pending_for("a")
    assert selection.excluded_for("a") is None
