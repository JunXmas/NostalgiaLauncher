"""Thông báo mới đóng theo phiên bản; changelog cuộn riêng, nút cập nhật luôn trong cửa sổ."""

from typing import Any

import pytest
from PySide6.QtCore import Property, QPointF, Slot
from PySide6.QtTest import QTest
from test_bridges import wait_until
from test_minimal_preview import Preview
from test_minimal_preview import preview as preview
from test_update_banner import FakeUpdateBridge

from qt_controls import find_control, press, wheel

pytestmark = pytest.mark.usefixtures("qt_app")


class ModernUpdateFixture(FakeUpdateBridge):
    @Property(str, constant=True)
    def releaseNotes(self) -> str:
        return (
            "## Bản mới\n"
            + "\n- Cải thiện giao diện và sửa lỗi.\n" * 50
            + "<details>SHA256</details>"
        )

    @Property(str, constant=True)
    def message(self) -> str:
        return "Sẵn sàng cập nhật."

    @Slot()
    def checkNow(self) -> None:
        self.calls.append("check")

    @Slot()
    def applyAndRestart(self) -> None:
        self.calls.append("apply")


def test_modern_update_notice_changelog_and_small_window_actions(preview: Preview) -> None:
    _launcher, view, _bridge, root_item = preview
    fake = ModernUpdateFixture()
    view.rootContext().setContextProperty("updateBridge", fake)
    root_item.setProperty("sessionSkipped", True)
    notice = find_control(root_item, "modernUpdateNotice")
    assert not notice.property("active")
    fake.set_state("available")
    assert notice.property("active")
    view.resize(1024, 600)
    view.rootContext().contextProperty("settingsBridge").setAppearance(150, False, True, True, "vi")
    press(view, find_control(root_item, "modernUpdateDetails"))
    dialog = find_control(root_item, "modernUpdateDialog")
    wait_until(lambda: bool(dialog.property("opened")))
    assert "SHA256" not in find_control(dialog, "updateChangelog").property("text")
    action: Any = find_control(dialog, "modernUpdateNow")
    p = action.mapToScene(QPointF())
    assert p.y() > 0 and p.y() + action.height() <= view.height()
    scroll = find_control(dialog, "updateChangelogScroll")
    wheel(view, scroll)
    QTest.qWait(120)
    assert scroll.property("contentY") > 0
    press(view, action)
    assert fake.calls == ["update"]
    fake.set_state("downloading")
    assert not action.property("clickable")
    fake.set_state("ready")
    press(view, action)
    assert fake.calls == ["update", "apply"]
    dialog.close()
    QTest.qWait(30)
    press(view, find_control(root_item, "modernUpdateDismiss"))
    assert not notice.property("active")
