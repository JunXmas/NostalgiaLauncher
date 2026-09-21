"""Toggle và Slider kiểu Bedrock: dựng thật, gọi thật, đọc lại hình khối.

Vì sao đáng có: hai widget này là hình, mà hình thì test dễ dừng ở "nạp được" rồi bỏ qua
việc núm trượt sai bên hay giá trị kéo ra ngoài khoảng. Ở đây kiểm đúng hai thứ đó, cộng
với API mà bốn chỗ gọi trong SettingsPage phụ thuộc vào.

Tín hiệu QML không lộ ra thành thuộc tính Python trên `QObject` trần, nên mỗi phép thử ghi
kết quả vào một thuộc tính khai ngay trong đoạn QML rồi đọc lại — đúng đường mà QML đi.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6", reason="giao diện là phụ thuộc tuỳ chọn: uv sync --extra ui")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = pytest.mark.usefixtures("qt_app")

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "nostalgia" / "ui" / "qml"

# Engine hoặc component chết thì cả cây QML chúng dựng chết theo, và test đỏ vì "Internal
# C++ object already deleted" chứ không vì widget sai. Giữ cả ba sống tới hết phiên.
LIVE_OBJECTS: list[object] = []

def build(source: str) -> QObject:
    """Dựng một đoạn QML trong thư mục qml thật, và coi MỌI lỗi là hỏng."""
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    qml_component = QQmlComponent(engine)
    qml_component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "probe.qml")))
    scene = qml_component.create()
    assert not qml_component.errors(), [e.toString() for e in qml_component.errors()]
    assert scene is not None
    QQmlEngine.setObjectOwnership(scene, QQmlEngine.CppOwnership)
    LIVE_OBJECTS.extend((engine, qml_component, scene))
    return scene

def find(scene: QObject, name: str) -> QObject:
    found = scene.findChild(QObject, name)
    assert found is not None, f"không thấy phần tử {name!r}"
    return found

def call(widget: QObject, method: str, argument: float) -> None:
    assert QMetaObject.invokeMethod(
        widget, method, Qt.DirectConnection, Q_ARG("QVariant", argument)
    ), f"không gọi được {method}()"

def test_toggle_keeps_the_api_the_settings_page_calls() -> None:
    """`checked` + `toggled(bool)` là hợp đồng với SettingsPage.qml:101,117,134,150.
    Đổi kiểu vẽ được, đổi hợp đồng thì bốn chỗ đó câm lặng."""
    scene = build(
        'import QtQuick\n'
        'Item { property string heard: ""\n'
        '  Toggle { objectName: "probe"; checked: false\n'
        '    onToggled: function (checked) { parent.heard += String(checked) + ";" } } }'
    )
    toggle = find(scene, "probe")

    assert toggle.property("checked") is False
    toggle.toggled.emit(True)
    QGuiApplication.processEvents()

    assert scene.property("heard") == "true;", "tín hiệu toggled(bool) phải còn nguyên chữ ký"

def test_toggle_is_a_square_block_not_a_pill() -> None:
    """Ảnh mẫu là ô vuông góc nhọn. Một `radius` lén vào là trôi ngược về kiểu iOS cũ."""
    toggle = find(build('import QtQuick\nItem { Toggle { objectName: "probe" } }'), "probe")

    assert (toggle.property("width"), toggle.property("height")) == (44, 24)
    radii = [child.property("radius") for child in toggle.findChildren(QObject)]
    assert all(radius in (None, 0) for radius in radii), f"khối Bedrock không bo góc: {radii}"

def test_the_toggle_knob_and_mark_swap_sides_when_it_flips() -> None:
    """Bật thì núm sang phải và ký hiệu là `I`; tắt thì ngược lại. Núm đứng yên = công tắc
    không nói được trạng thái của chính nó."""
    scene = build('import QtQuick\nItem { Toggle { objectName: "probe"; checked: false } }')
    toggle = find(scene, "probe")
    knob, mark = find(toggle, "toggleKnob"), find(toggle, "toggleMark")
    QGuiApplication.processEvents()

    assert knob.property("x") == 0
    assert mark.property("text") == "O"
    assert mark.property("x") > 0, "ký hiệu nằm ở nửa KHÔNG có núm"

    toggle.setProperty("checked", True)
    QGuiApplication.processEvents()

    assert mark.property("text") == "I"
    assert mark.property("x") == 0

def test_the_slider_reports_the_value_it_was_moved_to() -> None:
    """Kéo tới giữa quãng chạy phải ra giữa khoảng giá trị, và phải phát `moved`."""
    scene = build(
        'import QtQuick\n'
        'Item { property real lastMoved: -1\n'
        '  Slider { objectName: "probe"; from: 0; to: 100; value: 0; width: 204\n'
        '    onMoved: function (value) { parent.lastMoved = value } } }'
    )
    slider = find(scene, "probe")

    # Đúng giữa quãng chạy của núm: nửa quãng cộng nửa bề ngang núm.
    call(slider, "moveTo", slider.property("travel") / 2 + slider.property("knobWidth") / 2)

    assert scene.property("lastMoved") == pytest.approx(50.0)
    assert slider.property("value") == pytest.approx(50.0)

def test_the_slider_clamps_instead_of_flinging_the_knob_off_the_track() -> None:
    """Giá trị ngoài khoảng đến từ dữ liệu thật (RAM đã lưu lớn hơn `to` mới). Núm phải
    dừng ở mép, không bay ra khỏi rãnh."""
    slider = find(
        build('import QtQuick\nItem { Slider { objectName: "probe"; from: 1; to: 8; value: 99; width: 204 } }'),
        "probe",
    )

    assert slider.property("fraction") == 1.0
    call(slider, "moveTo", -500.0)
    assert slider.property("value") == pytest.approx(1.0)
    call(slider, "moveTo", 5000.0)
    assert slider.property("value") == pytest.approx(8.0)

def test_a_zero_width_range_does_not_divide_by_zero() -> None:
    """`from == to` xảy ra khi danh sách lựa chọn co lại còn một. NaN ở đây làm núm biến mất."""
    slider = find(
        build('import QtQuick\nItem { Slider { objectName: "probe"; from: 4; to: 4; value: 4; width: 204 } }'),
        "probe",
    )

    assert slider.property("fraction") == 0
    call(slider, "moveTo", 120.0)
    assert slider.property("value") == pytest.approx(4.0)
