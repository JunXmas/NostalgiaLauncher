"""Khách miễn phí thấy offer tự động, chờ host chia sẻ muộn, và không có thẻ tràn khung."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import find_control, press

from nostalgia.api import Instance, Launcher
from nostalgia.content.model import SearchPage
from nostalgia.multiplayer.model import RoomStatus
from nostalgia.multiplayer.sync_model import SyncFile, SyncManifest, SyncSnapshot
from nostalgia.operations.cancellation import CancelToken
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background
from social_fixture import SocialFixture

pytestmark = pytest.mark.usefixtures("qt_app")


class OfferGateway:
    def __init__(self) -> None:
        self.available = True
        self.manifest = SyncManifest(
            "Cuối tuần cùng bạn bè",
            "1.20.1",
            "forge",
            "47.4.23",
            (SyncFile("mods/example.jar", hashlib.sha256(b"fixture").hexdigest(), 7),),
        )

    def publish(
        self,
        room_code: str,
        host_ticket: str,
        snapshot: SyncSnapshot,
        *,
        cancel_token: CancelToken | None = None,
    ) -> None:
        del room_code, host_ticket, snapshot, cancel_token
        raise AssertionError("guest must not publish")

    def resolve(self, room_code: str) -> SyncManifest | None:
        assert room_code == "ABCDEFGHJKMNPQRSTU"
        return self.manifest if self.available else None

    def download(self, room_code: str, sync_file: SyncFile) -> bytes:
        del room_code, sync_file
        return b"fixture"


@pytest.fixture
def room_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, ...]]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    launcher.add_offline_account("JunXmas")
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    gateway = OfferGateway()
    social_gateway = SocialFixture()
    social_gateway.access_token = "a" * 64
    view, bridge = open_preview(launcher, room_sync_gateway=gateway, social_gateway=social_gateway)
    social_bridge = view.rootContext().contextProperty("socialBridge")
    wait_until(lambda: social_bridge.signedIn and not social_bridge.busy)
    view.show()
    view.requestActivate()
    root_item = view.rootObject()
    assert root_item is not None
    root_item.setProperty("currentIndex", 4)
    QTest.qWait(60)
    multiplayer = view.rootContext().contextProperty("multiplayerBridge")
    sync_bridge = view.rootContext().contextProperty("roomSyncBridge")
    sync_bridge._joined_code = "ABCDEFGHJKMNPQRSTU"
    yield launcher, gateway, view, root_item, multiplayer, sync_bridge, bridge
    social_bridge.shutdown()
    sync_bridge.cancel()
    sync_bridge._poll.stop()
    multiplayer.shutdown()
    bridge.cancelSignIn()
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def test_free_guest_sees_offer_and_creates_new_instance(
    room_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher, gateway, view, root_item, multiplayer, sync_bridge, bridge = room_preview
    received = []

    def install_fixture(
        self: Launcher,
        transport: object,
        code: str,
        manifest: SyncManifest,
        *,
        cancel_token: CancelToken,
        excluded_paths: frozenset[str],
    ) -> Instance:
        assert not excluded_paths
        cancel_token.raise_if_cancelled()
        received.append((transport, code, manifest))
        return self.create_instance(Instance("room-fixture", "1.20.1-forge-47.4.23", manifest.name))

    monkeypatch.setattr(Launcher, "sync_room_modpack", install_fixture)
    multiplayer._apply_status(RoomStatus(role="joined", local_port=25566))
    wait_until(lambda: bool(sync_bridge.property("offer")) and not sync_bridge.property("busy"))
    press(view, find_control(root_item, "syncRoomPackButton"))
    wait_until(lambda: sync_bridge.reviewReady and not sync_bridge.busy)
    assert not received
    assert not sync_bridge.confirmSync(False)
    press(view, find_control(root_item, "guestSyncConsent"))
    press(view, find_control(root_item, "guestSyncConfirm"))
    wait_until(lambda: bool(sync_bridge.property("note")))
    assert received == [(gateway, "ABCDEFGHJKMNPQRSTU", gateway.manifest)]
    assert len(launcher.list_instances()) == 1
    assert any(row["instanceId"] == "room-fixture" for row in bridge.property("instances"))


def test_offer_appears_when_host_publishes_after_guest_joined(
    room_preview: tuple[Any, ...],
) -> None:
    _, gateway, _, _, multiplayer, sync_bridge, _ = room_preview
    gateway.available = False
    sync_bridge._poll.setInterval(40)
    multiplayer._apply_status(RoomStatus(role="joined", local_port=25566))
    wait_until(lambda: not sync_bridge.property("busy"))
    assert not sync_bridge.property("offer")
    gateway.available = True
    wait_until(lambda: bool(sync_bridge.property("offer")))
    assert not sync_bridge._poll.isActive()
    multiplayer._apply_status(RoomStatus())
    assert not sync_bridge.property("offer")


@pytest.mark.parametrize("scale", [100, 150])
def test_sync_card_controls_fit_at_small_and_desktop_sizes(
    room_preview: tuple[Any, ...], scale: int
) -> None:
    _, _, view, root_item, multiplayer, sync_bridge, _ = room_preview
    multiplayer._apply_status(RoomStatus(role="joined", local_port=25566))
    wait_until(lambda: bool(sync_bridge.property("offer")))
    for width, height in [(1440, 900), (1024, 600)]:
        view.resize(width, height)
        view.rootContext().contextProperty("settingsBridge").setAppearance(
            scale, False, False, True, "vi"
        )
        QTest.qWait(80)
        card = find_control(root_item, "roomSyncCard")
        button = find_control(root_item, "syncRoomPackButton")
        origin = button.mapToItem(card, QPointF())
        assert origin.x() >= 0 and origin.y() >= 0
        assert origin.x() + button.width() <= card.width() + 0.5
        assert origin.y() + button.height() <= card.height() + 0.5
        scroll = find_control(root_item, "friendsScroll")
        assert card.width() <= scroll.width()
