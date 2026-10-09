"""Quyền server tự kiểm tra, chờ tác vụ trước và bỏ kết quả phiên Google cũ."""

from pathlib import Path
from threading import Event

import pytest
from test_bridges import wait_until

from nostalgia.api import ServerAccess
from nostalgia.ui.server_controller import ServerController
from nostalgia.ui.worker import wait_for_background
from server_fixture import ServerAccountFixture, server_launcher

pytestmark = pytest.mark.usefixtures("qt_app")


def test_access_waits_for_catalog_without_losing_either_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, _client = server_launcher(tmp_path)
    controller = ServerController(launcher, ServerAccountFixture(), enabled=True)
    entered, release = Event(), Event()

    def versions(_engine_id: str) -> tuple[str, ...]:
        entered.set()
        assert release.wait(3)
        return ("1.21.1",)

    monkeypatch.setattr(controller.domain_manager, "versions", versions)
    try:
        controller.loadVersions("paper")
        wait_until(entered.is_set)
        controller.checkAccess()
        assert not bool(controller.property("hasAccess"))
        release.set()
        wait_until(lambda: bool(controller.property("hasAccess")) and not controller.busy)
        assert controller.property("gameVersions") == ["1.21.1"]
    finally:
        release.set()
        controller.shutdown()
        wait_for_background()


def test_session_change_rechecks_automatically_and_ignores_old_grant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, _client = server_launcher(tmp_path)
    previous = ServerAccountFixture()
    entered, release = Event(), Event()

    def authorize() -> ServerAccess:
        entered.set()
        assert release.wait(3)
        return ServerAccess("Pro")

    monkeypatch.setattr(previous, "authorize", authorize)
    controller = ServerController(launcher, previous, enabled=True)
    try:
        controller.checkAccess()
        wait_until(entered.is_set)
        controller.set_gateway(ServerAccountFixture("Plus"))
        release.set()
        wait_until(lambda: not controller.busy and "cần Pro" in str(controller.property("note")))
        assert not bool(controller.property("hasAccess"))
        controller.set_gateway(ServerAccountFixture("Max"))
        wait_until(lambda: bool(controller.property("hasAccess")) and not controller.busy)
        assert "Max" in str(controller.property("note"))
        controller.set_gateway(None)
        wait_until(lambda: not controller.busy and "tạm khoá" in str(controller.property("note")))
        assert not bool(controller.property("hasAccess"))
    finally:
        release.set()
        controller.shutdown()
        wait_for_background()
