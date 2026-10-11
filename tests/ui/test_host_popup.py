"""Real Qt selector, locked Plus, keyboard choice and bounded mica popup on small displays."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPointF, Qt, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import find_control, press

from nostalgia.api import Instance, Launcher
from nostalgia.content.model import SearchPage
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background
from social_fixture import SocialFixture

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def host_popup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, ...]]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(
            launcher.load_settings(),
            auto_update_check=False,
            discord_presence=False,
            notification_sound=False,
            ui_sound=False,
        )
    )
    launcher.add_offline_account("JunPreview")
    launcher.create_instance(Instance("a", "1.21.1-fabric-0.16.10", "Cozy Adventures"))
    launcher.create_instance(Instance("b", "1.20.1-forge-47.4.23", "Better MC · Forge"))
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    gateway = SocialFixture()
    gateway.access_token = "a" * 64
    warnings: list[str] = []
    previous = qInstallMessageHandler(lambda _level, _context, message: warnings.append(message))
    view, bridge = open_preview(launcher, social_gateway=gateway, plus_enabled=False)
    social = view.rootContext().contextProperty("socialBridge")
    multiplayer = view.rootContext().contextProperty("multiplayerBridge")
    host = view.rootContext().contextProperty("hostBridge")
    wait_until(lambda: social.property("signedIn") and not social.property("busy"))
    view.show()
    root_item = view.rootObject()
    root_item.setProperty("currentIndex", 4)
    QTest.qWait(60)
    try:
        yield launcher, view, bridge, root_item, host, warnings
    finally:
        host.stop()
        social.shutdown()
        multiplayer.shutdown()
        bridge.cancelSignIn()
        wait_for_background()
        view.close()
        view.deleteLater()
        QGuiApplication.processEvents()
        qInstallMessageHandler(previous)


def test_open_room_selects_installed_pack_before_any_launch(
    host_popup: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, view, bridge, root_item, host, warnings = host_popup
    launched = []
    monkeypatch.setattr(
        bridge, "play_hosted", lambda instance_id, *_args: launched.append(instance_id)
    )
    press(view, find_control(root_item, "friendsOpenRoom"))
    popup = find_control(root_item, "hostDialog")
    wait_until(lambda: popup.property("opened"))
    assert find_control(root_item, "friendsPage").property("section") == 1
    assert not host.property("details")["active"] and not launched
    sharing = find_control(root_item, "hostSharePack")
    assert not sharing.property("enabled") and not sharing.property("checked")
    picker = find_control(root_item, "hostPackPicker")
    press(view, picker, Qt.Key.Key_Space)
    wait_until(lambda: find_control(root_item, "hostPackPickerMenu").property("opened"))
    QTest.keyClick(view, Qt.Key.Key_Down)
    QTest.keyClick(view, Qt.Key.Key_Return)
    wait_until(lambda: picker.property("currentIndex") == 1)
    assert "forge" in find_control(root_item, "hostSelectedVersion").property("text")
    press(view, find_control(root_item, "hostLaunchButton"))
    wait_until(lambda: not popup.property("visible"))
    assert launched == ["b"] and host.property("details")["instanceId"] == "b"
    assert not host.property("details")["share"]
    assert not warnings, "\n".join(warnings)


@pytest.mark.parametrize("scale", [100, 150])
def test_host_popup_mica_and_footer_fit_small_windows(
    host_popup: tuple[Any, ...], scale: int
) -> None:
    _, view, _, root_item, host, warnings = host_popup
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(
        scale, False, False, True, "vi"
    )
    host.openSetup()
    popup = find_control(root_item, "hostDialog")
    wait_until(lambda: popup.property("opened"))
    QTest.qWait(80)
    mica = find_control(root_item, "hostDialogMica")
    launch = find_control(root_item, "hostLaunchButton")
    assert popup.property("width") <= view.width() - 48
    assert popup.property("height") <= view.height() - 48
    origin = mica.mapToScene(QPointF())
    assert mica.property("backdropRect").x() == pytest.approx(origin.x())
    assert mica.property("backdropRect").y() == pytest.approx(origin.y())
    button_origin = launch.mapToScene(QPointF())
    assert 0 <= button_origin.x() <= view.width() - launch.width()
    assert 0 <= button_origin.y() <= view.height() - launch.height()
    assert launch.property("clickable")
    assert not warnings, "\n".join(warnings)
