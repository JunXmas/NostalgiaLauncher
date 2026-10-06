"""Ô lọc thu gọn: đóng lại một ô, bấm mới bung khay; và khay KHÔNG cắt bớt danh mục.

Vì sao đáng có: bản cũ trải mọi phiên bản game thành hàng dọc trong cột lọc rồi `.slice(0, 60)`
cho vừa cột — người tìm bản 1.7.10 không bao giờ thấy nó, mà giao diện cũng không nói gì.
Hai test ở đây biến đúng hai chuyện đó thành CI đỏ: nhãn trên ô phải nói được đang lọc mấy
mục, và khay phải giữ nguyên số mục được đưa vào.
"""

from __future__ import annotations

import os
from typing import cast

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from test_qml_widgets import build, find

pytestmark = pytest.mark.usefixtures("qt_app")

# FilterChip đọc `contentBridge`/`catalogBridge`? Không — nó nhận `options`/`selected` qua
# thuộc tính, nên dựng được trơ trọi. Đó là lý do nó tách khỏi FilterBar.
CHIP = """
import QtQuick
Item {
  width: 400; height: 300
  property string heardValue: ""
  property bool heardChecked: false
  property int clearCount: 0
  FilterChip {
    objectName: "probe"
    width: 168
    title: "Mọi phiên bản"
    searchable: true
    options: %s
    selected: %s
    onToggled: function (value, checked) {
      parent.heardValue = value; parent.heardChecked = checked;
    }
    onCleared: parent.clearCount += 1
  }
}
"""


def versions(count: int) -> str:
    items = ", ".join(f'{{ value: "1.{n}", label: "1.{n}" }}' for n in range(count))
    return f"[{items}]"


def shown(chip: QObject) -> list[dict[str, str]]:
    """`shown` là mảng JS tính trong QML, sang Python thành `QJSValue` chứ không thành list."""
    from PySide6.QtQml import QJSValue

    value = chip.property("shown")
    items = value.toVariant() if isinstance(value, QJSValue) else value
    return cast("list[dict[str, str]]", items)


def test_the_chip_head_says_how_many_filters_are_on_without_being_opened() -> None:
    """Ô đóng phải nói được trạng thái: một mục thì hiện tên nó, nhiều mục thì tên + số còn
    lại. Ô câm thì người dùng không biết vì sao kho chỉ còn ba kết quả."""
    chip = find(build(CHIP % (versions(5), '["1.0"]')), "probe")
    QGuiApplication.processEvents()

    assert chip.property("headLabel") == "1.0"

    chip.setProperty("selected", ["1.0", "1.1", "1.2"])
    QGuiApplication.processEvents()

    assert chip.property("headLabel") == "1.0 +2"

    chip.setProperty("selected", [])
    QGuiApplication.processEvents()

    assert chip.property("headLabel") == "Mọi phiên bản", "không lọc gì thì hiện tiêu đề"


def test_the_tray_keeps_every_option_instead_of_trimming_the_catalogue() -> None:
    """Danh mục Mojang có hàng trăm bản. Khay cuộn được nên KHÔNG được cắt: cắt là người tìm
    bản cũ không bao giờ thấy nó (đúng bug của cột lọc cũ, `.slice(0, 60)`)."""
    chip = find(build(CHIP % (versions(300), "[]")), "probe")
    QGuiApplication.processEvents()

    assert len(shown(chip)) == 300


def test_searching_inside_the_tray_narrows_the_list_case_insensitively() -> None:
    chip = find(
        build(
            CHIP
            % ('[{ value: "fabric", label: "Fabric" }, { value: "forge", label: "Forge" }]', "[]")
        ),
        "probe",
    )

    chip.setProperty("filterText", "FAB")
    QGuiApplication.processEvents()

    assert [option["value"] for option in shown(chip)] == ["fabric"]


def test_the_tray_has_no_height_until_the_chip_is_opened() -> None:
    """Thu gọn là mục đích chính của widget này. Khay cao sẵn = hàng lọc lại chiếm cả trang."""
    scene = build(CHIP % (versions(30), "[]"))
    chip = find(scene, "probe")
    tray = find(chip, "filterChipTray")
    QGuiApplication.processEvents()

    assert tray.property("height") == 0
    assert tray.property("visible") is False

    chip.setProperty("open", True)
    QGuiApplication.processEvents()

    assert chip.property("open") is True


def test_the_clear_mark_only_appears_when_something_is_filtered() -> None:
    scene = build(CHIP % (versions(5), "[]"))
    chip = find(scene, "probe")
    clear_mark = find(chip, "filterChipClear")
    QGuiApplication.processEvents()

    assert clear_mark.property("visible") is False

    chip.setProperty("selected", ["1.0"])
    QGuiApplication.processEvents()

    assert clear_mark.property("visible") is True
    chip.cleared.emit()  # type: ignore[attr-defined]
    QGuiApplication.processEvents()
    assert scene.property("clearCount") == 1


def test_changing_the_selection_does_not_create_a_text_width_binding_loop() -> None:
    from PySide6.QtCore import qInstallMessageHandler

    warnings: list[str] = []
    qInstallMessageHandler(lambda _kind, _context, message: warnings.append(message))
    try:
        chip = find(build(CHIP % (versions(5), "[]")), "probe")
        for selection in (["1.0"], ["1.0", "1.1"], [], ["1.2"]):
            chip.setProperty("selected", selection)
            QGuiApplication.processEvents()
        assert find(chip, "filterChipClear").property("width") > 8
    finally:
        qInstallMessageHandler(None)
    assert warnings == []
