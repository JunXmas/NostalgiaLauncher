"""Slide quảng cáo trên trang chủ: server vào thẳng bằng bản chơi đang chọn, link mở trình duyệt."""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtTest import QTest
from qml_tree import find_item
from test_bridges import wait_until

from nostalgia.api import Instance, Launcher, Promotion
from nostalgia.ui.bridge import LauncherBridge
from nostalgia.ui.window import open_window
from nostalgia.ui.worker import wait_for_background
from qt_controls import press

pytestmark = pytest.mark.usefixtures("qt_app")

SLIDES = (
    Promotion(
        "server", "Server cộng đồng", "Sinh tồn", "Vào server", "play.x.vn:25565", None, 0, 0
    ),
    Promotion("link", "Thuê server", "", "Xem giá", "https://host.x.vn/thue", None, 0, 0),
    Promotion("link", "Đã hết hạn", "", "Xem", "https://old.x.vn", None, 0, int(time.time()) - 1),
)


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, ...]]:
    launcher = Launcher.for_data_dir(tmp_path / "data", tmp_path / "settings")
    launcher.save_settings(
        replace(launcher.load_settings(), auto_update_check=False, discord_presence=False)
    )
    launcher.add_offline_account("Jun")
    launcher.create_instance(Instance("sinh-ton", "1.21.11", "Sinh tồn"))
    monkeypatch.setattr(Launcher, "load_promotions", lambda _self: SLIDES)
    opened: list[str] = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toString()))
    played: list[tuple[str, str]] = []
    monkeypatch.setattr(LauncherBridge, "playServer", lambda _b, i, a: played.append((i, a)))
    view, _bridge = open_window(launcher)
    root_item = view.rootObject()
    root_item.setProperty("loginVisible", False)
    view.show()
    slides = view.rootContext().contextProperty("promotionBridge")
    wait_until(lambda: len(slides.property("slides")) == 2)
    QTest.qWait(80)
    yield view, root_item, slides, opened, played
    wait_for_background()
    view.close()
    view.deleteLater()
    QGuiApplication.processEvents()


def test_expired_slides_hide_and_each_kind_does_its_own_action(home: tuple[Any, ...]) -> None:
    view, root_item, slides, opened, played = home
    assert [s["title"] for s in slides.property("slides")] == ["Server cộng đồng", "Thuê server"]
    carousel = find_item(root_item, "homeSlides")
    assert carousel is not None and carousel.property("count") == 3
    actions = []

    def collect(node: Any) -> None:
        if node.objectName() == "promotionAction":
            actions.append(node)
        for child in node.childItems():
            collect(child)

    collect(carousel)
    assert len(actions) == 2
    carousel.setProperty("current", 1)
    QTest.qWait(700)
    press(view, actions[0])
    assert played == [("sinh-ton", "play.x.vn:25565")] and opened == []
    carousel.setProperty("current", 2)
    QTest.qWait(700)
    press(view, actions[1])
    assert opened == ["https://host.x.vn/thue"]
    # QML không mở được địa chỉ ngoài feed đã kiểm.
    slides.openLink("https://evil.example/")
    slides.openLink("https://old.x.vn")
    assert opened == ["https://host.x.vn/thue"]
