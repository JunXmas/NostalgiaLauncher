"""Dải báo bản mới ở đầu vùng nội dung: hiện đúng lúc, nhãn đúng trạng thái, nút gọi đúng
cầu nối, và đóng được.

Vì sao đáng có: trước đây bản mới chỉ nằm trong CÀI ĐẶT → CẬP NHẬT nên không ai thấy. Nếu
dải này lặng lẽ ngừng hiện (đổi tên trạng thái, đổi thuộc tính), không gì khác đỏ.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = pytest.mark.usefixtures("qt_app")

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "nostalgia" / "ui" / "qml"

LIVE_OBJECTS: list[object] = []


class FakeUpdateBridge(QObject):
    """Cầu nối giả, đúng bề mặt mà UpdateBanner.qml đụng tới."""

    stateChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._state = "idle"
        self.calls: list[str] = []

    def set_state(self, state: str) -> None:
        self._state = state
        self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def state(self) -> str:
        return self._state

    @Property(str, notify=stateChanged)
    def latestVersion(self) -> str:
        return "9.9.9"

    @Property(str, constant=True)
    def installKind(self) -> str:
        return "frozen"

    @Property(float, notify=stateChanged)
    def progressFraction(self) -> float:
        return 0.5

    @Slot()
    def updateNow(self) -> None:
        self.calls.append("update")

    @Slot()
    def openReleasePage(self) -> None:
        self.calls.append("open")


def build_banner() -> tuple[QObject, FakeUpdateBridge]:
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    fake = FakeUpdateBridge()
    engine.rootContext().setContextProperty("updateBridge", fake)
    qml_component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "UpdateBanner.qml")))
    banner = qml_component.create()
    assert not qml_component.errors(), [e.toString() for e in qml_component.errors()]
    assert banner is not None
    QQmlEngine.setObjectOwnership(banner, QQmlEngine.CppOwnership)  # type: ignore[attr-defined]
    LIVE_OBJECTS.extend((engine, qml_component, banner, fake))
    return banner, fake


def text_of(banner: QObject) -> str:
    caption = banner.findChild(QObject, "updateBannerText")
    assert caption is not None
    return str(caption.property("text"))


def test_banner_stays_out_of_the_way_until_there_is_something_to_do() -> None:
    banner, fake = build_banner()
    assert banner.property("active") is False
    for quiet in ("idle", "checking", "failed"):
        fake.set_state(quiet)
        assert banner.property("active") is False, quiet


def test_banner_shows_each_stage_and_drives_the_bridge() -> None:
    banner, fake = build_banner()

    fake.set_state("available")
    assert banner.property("active") is True
    assert "9.9.9" in text_of(banner)
    update_button = banner.findChild(QObject, "bannerUpdateButton")
    assert update_button is not None and banner.property("canUpdate")
    assert update_button.property("label") == "⬇  Cập nhật ngay"
    update_button.metaObject().invokeMethod(update_button, "clicked")
    assert fake.calls == ["update"]

    # Một nút là đủ: tải và cài là hai nhịp của cùng một lần bấm, nên sau khi bấm thì không
    # còn nút nào để bấm nữa — chỉ còn chữ báo tiến trình.
    fake.set_state("downloading")
    assert "50%" in text_of(banner)
    assert banner.property("canUpdate") is False

    fake.set_state("ready")
    assert banner.property("canUpdate") is False
    assert "mở lại" in text_of(banner)


def test_dismissing_the_banner_silences_it() -> None:
    banner, fake = build_banner()
    fake.set_state("available")
    banner.setProperty("dismissed", True)
    assert banner.property("active") is False
