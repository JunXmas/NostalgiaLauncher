"""Khay chọn bản chơi trên trang chủ (mở lên trên, đè lên nút CHƠI): bấm mục nào cũng chọn được
mục đó, và cú bấm KHÔNG lọt xuống nút CHƠI phía dưới."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtTest import QTest
from test_qml import make_launcher

from nostalgia.instance.model import Instance
from nostalgia.ui.app import build_view

pytestmark = pytest.mark.usefixtures("qt_app")


def test_every_row_is_selectable_and_nothing_leaks_to_the_play_button(tmp_path: Path) -> None:
    launcher = make_launcher(tmp_path)
    for position in range(4):
        launcher.create_instance(
            Instance(
                instance_id=f"ban-{position}", version_id="1.99.9", display_name=f"Bản {position}"
            )
        )
    launcher.add_offline_account("Jun")
    view, bridge = build_view(launcher)
    view.show()
    QGuiApplication.processEvents()
    root_item = view.rootObject()
    assert root_item is not None
    home = root_item.findChild(QObject, "homePage")
    picker = root_item.findChild(QObject, "homeInstancePicker")
    assert home is not None and picker is not None
    leaks: list[str] = []
    bridge.failed.connect(leaks.append)
    bridge.gameStarted.connect(lambda instance_id: leaks.append(f"play:{instance_id}"))

    for wanted in (3, 1, 2, 0):
        picker.setProperty("open", True)
        QTest.qWait(250)  # chiều cao khay có hoạt ảnh mở ra
        QGuiApplication.processEvents()
        popup = picker.findChild(QObject, "dropdownPopup")
        assert popup is not None and popup.property("visible") is True
        # Hàng `wanted` nằm ở y = lề 4 + 32 * wanted trong khay; khay mở LÊN TRÊN nên các hàng
        # đầu đè thẳng lên nút CHƠI — đúng chỗ cú bấm từng lọt xuống.
        point = popup.mapToScene(QPointF(30, 4 + 32 * wanted + 16))
        QTest.mouseClick(
            view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point.toPoint()
        )
        QGuiApplication.processEvents()
        assert home.property("chosenIndex") == wanted, f"bấm hàng {wanted} phải chọn được nó"
        assert picker.property("open") is False, "chọn xong khay phải đóng"

    QTest.qWait(200)
    QGuiApplication.processEvents()
    assert leaks == [], "bấm trong khay không được kích hoạt nút CHƠI"
    assert bridge.busy is False
