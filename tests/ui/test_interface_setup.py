"""Thiết lập hai giao diện, lưu lựa chọn và đổi lại qua Cài đặt bằng Qt thật."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from threading import Event
from typing import Any

import pytest

pytest.importorskip("PySide6")
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until
from test_minimal_preview import press
from test_payment_layout import assert_within

from nostalgia.api import Instance, Launcher
from nostalgia.content.model import SearchPage
from nostalgia.errors import DataFileError
from nostalgia.ui.preview import open_preview
from nostalgia.ui.worker import wait_for_background

pytestmark = pytest.mark.usefixtures("qt_app")


@pytest.fixture
def setup_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, ...]]:
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
    monkeypatch.setattr(Launcher, "search_content", lambda *_a, **_k: SearchPage((), 0, 0))
    view, bridge = open_preview(launcher, ui_setup=True)
    assert view.rootObject() is not None, [error.toString() for error in view.errors()]
    view.show()
    view.requestActivate()
    QTest.qWait(60)
    settings = view.rootContext().contextProperty("settingsBridge")
    yield launcher, view, bridge, settings
    bridge.cancelSignIn()
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def find_control(root_item: Any, name: str) -> Any:
    control = find_item(root_item, name)
    assert control is not None, name
    return control


def choose(view: Any, style: str) -> None:
    root_item = view.rootObject()
    press(view, find_control(root_item, "interfaceChoice-" + style))
    assert root_item.property("selectedStyle") == style
    press(view, find_control(root_item, "interfaceChoiceContinue"))
    wait_until(lambda: view.rootObject().objectName() != "interfaceChooser")


@pytest.mark.parametrize("style", ["classic", "modern"])
def test_first_choice_persists_and_next_window_skips_setup(
    setup_preview: tuple[Any, ...], style: str
) -> None:
    launcher, view, _bridge, settings = setup_preview
    root_item = view.rootObject()
    assert root_item.objectName() == "interfaceChooser"
    assert not find_control(root_item, "interfaceChoiceContinue").property("clickable")
    choose(view, style)
    assert launcher.load_settings().interface_style == style
    assert settings.interfaceStyle == style
    if style == "classic":
        assert find_control(view.rootObject(), "sidebar")
    else:
        assert view.rootObject().property("loginVisible")
    second_view, second_bridge = open_preview(launcher, ui_setup=True)
    assert second_view.rootObject().objectName() != "interfaceChooser"
    assert (second_view.rootObject().objectName() == "minimalPreview") == (style == "modern")
    second_bridge.cancelSignIn()
    wait_for_background()
    second_view.close()
    second_view.deleteLater()
    QGuiApplication.processEvents()


@pytest.mark.parametrize("scale", [100, 150])
def test_small_setup_has_real_images_and_keeps_continue_visible(
    setup_preview: tuple[Any, ...], scale: int
) -> None:
    _launcher, view, _bridge, settings = setup_preview
    view.resize(1024, 600)
    settings.setAppearance(scale, False, False, True, "vi")
    QTest.qWait(80)
    root_item = view.rootObject()
    for style in ("classic", "modern"):
        image = find_control(root_item, "interfaceImage-" + style)
        assert image.implicitWidth() > 0 and image.implicitHeight() > 0
        card = find_control(root_item, "interfaceChoice-" + style)
        assert_within(image, card)
        assert_within(card, find_control(root_item, "interfaceChoiceScroll"))
    assert_within(find_control(root_item, "interfaceChoiceContinue"), root_item)
    choose(view, "modern")


def test_change_and_cancel_preserve_accounts_and_return_to_settings(
    setup_preview: tuple[Any, ...],
) -> None:
    launcher, view, bridge, settings = setup_preview
    launcher.add_offline_account("JunPreview")
    instance = launcher.create_instance(Instance("keep-mods", "1.20.1"))
    sentinel = launcher.instance_game_dir(instance) / "options.txt"
    sentinel.write_text("preview settings")
    bridge.announce_accounts_changed()
    choose(view, "classic")
    sidebar = find_control(view.rootObject(), "sidebar")
    sidebar.setProperty("currentIndex", 6)
    QTest.qWait(80)
    press(view, find_control(view.rootObject(), "interfaceChoiceChange"))
    wait_until(lambda: view.rootObject().objectName() == "interfaceChooser")
    press(view, find_control(view.rootObject(), "interfaceChoice-modern"))
    press(view, find_control(view.rootObject(), "interfaceChoiceCancel"))
    wait_until(lambda: view.rootObject().objectName() != "interfaceChooser")
    assert settings.interfaceStyle == "classic"
    assert find_control(view.rootObject(), "sidebar").property("currentIndex") == 6
    press(view, find_control(view.rootObject(), "interfaceChoiceChange"))
    wait_until(lambda: view.rootObject().objectName() == "interfaceChooser")
    choose(view, "modern")
    assert bridge.activePlayerName == "JunPreview"
    assert launcher.list_instances() == (instance,)
    assert sentinel.read_text() == "preview settings"
    assert view.rootObject().property("currentIndex") == 6
    assert find_control(view.rootObject(), "interfaceChoiceChange")
    assert settings.interfaceStyle == "modern"
    settings.setAppearance(125, False, True, True, "vi")
    settings.setUiSound(False)
    assert launcher.load_settings().interface_style == "modern"


def test_switch_is_blocked_while_content_work_is_running(setup_preview: tuple[Any, ...]) -> None:
    launcher, view, _bridge, _settings = setup_preview
    setup = view.rootContext().contextProperty("interfaceSetup")
    content = view.rootContext().contextProperty("contentBridge")
    released = Event()
    content.run_in_background(lambda: released.wait(3), "Preview install")
    try:
        setup.choose("modern")
        setup.openChooser()
        QTest.qWait(30)
        assert launcher.load_settings().interface_style == ""
        assert view.rootObject().objectName() == "interfaceChooser"
    finally:
        released.set()
        wait_for_background()
    QTest.qWait(30)
    choose(view, "modern")


@pytest.mark.parametrize("error_type", [DataFileError, PermissionError])
def test_failed_save_keeps_setup_and_allows_retry(
    setup_preview: tuple[Any, ...], monkeypatch: pytest.MonkeyPatch, error_type: type[Exception]
) -> None:
    launcher, view, _bridge, settings = setup_preview
    root_item = view.rootObject()
    press(view, find_control(root_item, "interfaceChoice-modern"))
    with monkeypatch.context() as blocked:

        def fail_save(*_args: Any) -> None:
            raise error_type("Settings write failed")

        blocked.setattr(Launcher, "save_settings", fail_save)
        press(view, find_control(root_item, "interfaceChoiceContinue"))
        assert view.rootObject().objectName() == "interfaceChooser"
        assert settings.interfaceSelectionError
        assert launcher.load_settings().interface_style == ""
    choose(view, "modern")
    assert not settings.interfaceSelectionError
    assert not settings.setInterfaceStyle("unknown")
    assert launcher.load_settings().interface_style == "modern"
